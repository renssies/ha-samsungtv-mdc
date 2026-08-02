"""Config flow for the Samsung TV MDC integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.config_entries import (
    ConfigFlow as HAConfigFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from samsung_mdc import MDC
from samsung_mdc.exceptions import MDCTimeoutError, MDCTLSAuthFailed

from .const import (
    CONF_DISPLAY_ID,
    CONF_ENABLE_ENHANCEMENT,
    CONF_PIN,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENABLE_ENHANCEMENT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PIN_MIN_LENGTH = 4
PIN_MAX_LENGTH = 12
_MASKED_PIN_NONE = "none"


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return schema for device connection fields and interval."""
    scan_interval = defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    if isinstance(scan_interval, timedelta):
        scan_interval = int(scan_interval.total_seconds())
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                default=defaults.get(CONF_HOST, ""),
            ): str,
            vol.Required(
                CONF_DISPLAY_ID,
                default=int(defaults.get(CONF_DISPLAY_ID, 1)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=254,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_PORT,
                default=int(defaults.get(CONF_PORT, DEFAULT_PORT)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=65535,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=int(scan_interval),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=int(MIN_SCAN_INTERVAL.total_seconds()),
                    max=int(MAX_SCAN_INTERVAL.total_seconds()),
                ),
            ),
            vol.Required(
                CONF_ENABLE_ENHANCEMENT,
                default=bool(
                    defaults.get(
                        CONF_ENABLE_ENHANCEMENT, DEFAULT_ENABLE_ENHANCEMENT
                    )
                ),
            ): selector.BooleanSelector(),
        }
    )


STEP_USER_DATA_SCHEMA = _options_schema({})


async def _try_connect(host: str, display_id: int, port: int, pin: str | None) -> str:
    """Try connecting to device and return model string."""
    target = host if port == DEFAULT_PORT else f"{host}:{port}"

    _LOGGER.debug(
        "Connecting to MDC target %s display %s (pin:%s)",
        target,
        display_id,
        _masked_pin(pin),
    )
    try:
        async with MDC(target, timeout=DEFAULT_TIMEOUT, pin=pin) as client:
            status = await client.status(display_id)
    except MDCTLSAuthFailed as err:
        _LOGGER.debug("MDC TLS auth failed for %s: %s", target, err)
        raise InvalidAuth from err
    except (MDCTimeoutError, OSError) as err:
        _LOGGER.debug("MDC connection error for %s: %s", target, err)
        raise CannotConnect from err

    power_state = status[0].name if hasattr(status[0], "name") else str(status[0])
    return f"{target} ({power_state})"


async def validate_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Ensure numeric fields are integers even if selectors provide them as float.
    display_id = int(data[CONF_DISPLAY_ID])
    port = int(data[CONF_PORT])
    pin = _normalized_pin(data.get(CONF_PIN))
    display_name = await _try_connect(
        data[CONF_HOST],
        display_id,
        port,
        pin,
    )

    return {"title": display_name}


def _current_entry_values(entry: ConfigEntry) -> dict[str, Any]:
    """Return current connection values using options when present."""
    scan_interval: int | timedelta = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    if isinstance(scan_interval, timedelta):
        scan_interval = int(scan_interval.total_seconds() // 60)
    else:
        scan_interval = int(scan_interval)
    return {
        CONF_HOST: entry.options.get(CONF_HOST, entry.data.get(CONF_HOST, "")),
        CONF_DISPLAY_ID: int(
            entry.options.get(CONF_DISPLAY_ID, entry.data.get(CONF_DISPLAY_ID, 1))
        ),
        CONF_PORT: int(
            entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT))
            or DEFAULT_PORT
        ),
        CONF_PIN: entry.options.get(CONF_PIN, entry.data.get(CONF_PIN, "") or ""),
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_ENABLE_ENHANCEMENT: bool(
            entry.options.get(
                CONF_ENABLE_ENHANCEMENT,
                entry.data.get(CONF_ENABLE_ENHANCEMENT, DEFAULT_ENABLE_ENHANCEMENT),
            )
        ),
    }


def _merged_options(
    existing: dict[str, Any], settings: dict[str, Any]
) -> dict[str, Any]:
    """Merge updated connection values into current options."""
    new_options = dict(existing)
    new_options.update(settings)
    return new_options


def _update_entry_configuration(
    hass: Any,
    entry: ConfigEntry,
    settings: dict[str, Any],
) -> None:
    """Persist updated connection settings and reload entry."""
    new_data = dict(entry.data)
    new_data.update(
        {
            CONF_HOST: settings[CONF_HOST],
            CONF_DISPLAY_ID: settings[CONF_DISPLAY_ID],
            CONF_PORT: settings[CONF_PORT],
            CONF_PIN: settings[CONF_PIN],
        }
    )
    new_options = _merged_options(entry.options, settings)
    hass.config_entries.async_update_entry(entry, data=new_data, options=new_options)
    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))


def _masked_pin(pin: str | None) -> str:
    """Return masked pin length for logging."""
    if not pin:
        return _MASKED_PIN_NONE
    try:
        pin_length = len(str(pin))
    except Exception:  # noqa: BLE001
        return _MASKED_PIN_NONE
    return f"{pin_length}d"


def _normalized_pin(pin: str | None) -> str | None:
    """Return sanitized pin or raise for invalid input."""
    if not pin:
        return None
    pin_str = str(pin)
    if pin_str.isdigit() and PIN_MIN_LENGTH <= len(pin_str) <= PIN_MAX_LENGTH:
        return pin_str
    raise InvalidPin


class ConfigFlow(HAConfigFlow, domain=DOMAIN):
    """Handle a config flow for Samsung TV MDC."""

    VERSION = 1
    MINOR_VERSION = 1
    _reconfigure_entry: ConfigEntry | None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidPin:
                errors["pin"] = "invalid_pin"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}-{user_input[CONF_DISPLAY_ID]}"
                )
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_PIN: user_input.get(CONF_PIN),
                    }
                )
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfigure when entry is in error state."""
        errors: dict[str, str] = {}

        if self.context.get("entry_id") is None:
            return self.async_abort(reason="unknown")

        self._reconfigure_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if self._reconfigure_entry is None:
            return self.async_abort(reason="unknown")

        current_values = _current_entry_values(self._reconfigure_entry)

        if user_input is not None:
            host = user_input[CONF_HOST]
            display_id = int(user_input[CONF_DISPLAY_ID])
            port = int(user_input[CONF_PORT])
            try:
                pin_value = _normalized_pin(user_input.get(CONF_PIN))
            except InvalidPin:
                errors["pin"] = "invalid_pin"
                pin_value = None
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])

            if not errors:
                try:
                    await _try_connect(host, display_id, port, pin_value)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception:
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    settings = {
                        CONF_HOST: host,
                        CONF_DISPLAY_ID: display_id,
                        CONF_PORT: port,
                        CONF_PIN: pin_value,
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_ENABLE_ENHANCEMENT: bool(
                            user_input[CONF_ENABLE_ENHANCEMENT]
                        ),
                    }
                    _update_entry_configuration(
                        self.hass,
                        self._reconfigure_entry,
                        settings,
                    )
                    return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_options_schema(current_values),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)


class CannotConnect(HomeAssistantError):  # noqa: N818
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):  # noqa: N818
    """Error to indicate there is invalid auth."""


class InvalidPin(HomeAssistantError):  # noqa: N818
    """Error to indicate the provided PIN is invalid."""


class OptionsFlowHandler(OptionsFlow):
    """Handle options for Samsung TV MDC."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        current_values = _current_entry_values(self._entry)

        if user_input is not None:
            host = user_input[CONF_HOST]
            display_id = int(user_input[CONF_DISPLAY_ID])
            port = int(user_input[CONF_PORT])
            try:
                pin_value = _normalized_pin(user_input.get(CONF_PIN))
            except InvalidPin:
                errors["pin"] = "invalid_pin"
                pin_value = None
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])

            if not errors:
                try:
                    await _try_connect(host, display_id, port, pin_value)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception:
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    settings = {
                        CONF_HOST: host,
                        CONF_DISPLAY_ID: display_id,
                        CONF_PORT: port,
                        CONF_PIN: pin_value,
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_ENABLE_ENHANCEMENT: bool(
                            user_input[CONF_ENABLE_ENHANCEMENT]
                        ),
                    }
                    new_options = _merged_options(
                        self._entry.options,
                        settings,
                    )
                    return self.async_create_entry(
                        title="",
                        data=new_options,
                    )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current_values),
            errors=errors,
        )
