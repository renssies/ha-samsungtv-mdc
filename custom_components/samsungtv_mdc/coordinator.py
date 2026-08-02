"""Data coordinator for Samsung TV MDC."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from async_timeout import timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from samsung_mdc import MDC, commands
from samsung_mdc.exceptions import (
    MDCReadTimeoutError,
    MDCResponseError,
    MDCTimeoutError,
    NAKError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .const import (
    CONF_DISPLAY_ID,
    CONF_ENABLE_ENHANCEMENT,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENABLE_ENHANCEMENT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENHANCEMENT_CMD,
    ENHANCEMENT_OFF,
    ENHANCEMENT_ON,
    ENHANCEMENT_SUBCMD,
    PanelState,
)

CONNECTION_REFUSED_ERRNO = 111
UNKNOWN_VOLUME = 255


@dataclass
class SamsungMDCState:
    """Collected state from MDC."""

    power: commands.POWER.POWER_STATE
    volume: int | None
    mute: commands.MUTE.MUTE_STATE | None
    input_source: commands.INPUT_SOURCE.INPUT_SOURCE_STATE | None
    manual_lamp: int
    color_temperature_hk: int
    ticker: tuple[Any, ...]
    device_name: str | None
    serial_number: str | None
    model_name: str | None
    software_version: str | None
    color_enhancement: bool | None


class SamsungMDCDevice:
    """Wrapper around samsung_mdc client."""

    def __init__(
        self,
        host: str,
        display_id: int,
        port: int,
        pin: str | None,
        timeout: float,
    ) -> None:
        """Initialize MDC device wrapper."""
        self._logger = logging.getLogger(__name__)
        self._target = host if port == DEFAULT_PORT else f"{host}:{port}"
        self.display_id = display_id
        self._pin = pin
        self._timeout = timeout
        self._client = MDC(self._target, timeout=timeout, pin=pin)
        self._lock = asyncio.Lock()

    async def async_close(self) -> None:
        """Close the connection."""
        async with self._lock:
            if self._client.writer is None:
                return
            await self._client.close()

    async def async_set_power(self, state: commands.POWER.POWER_STATE) -> None:
        """Set display power state."""
        await self._call("power", [state])

    async def async_set_volume(self, volume: int) -> None:
        """Set display volume (0-100)."""
        await self._call("volume", [volume])

    async def async_volume_step(
        self, direction: commands.VOLUME_CHANGE.CHANGE_TO
    ) -> None:
        """Step volume up/down."""
        await self._call("volume_change", [direction])

    async def async_set_mute(self, muted: bool) -> None:  # noqa: FBT001
        """Set mute state."""
        state = commands.MUTE.MUTE_STATE.ON if muted else commands.MUTE.MUTE_STATE.OFF
        await self._call("mute", [state])

    async def async_set_input_source(
        self, source: commands.INPUT_SOURCE.INPUT_SOURCE_STATE
    ) -> None:
        """Set input source."""
        await self._call("input_source", [source])

    async def async_status(self) -> tuple[Any, ...]:
        """Fetch basic status."""
        return await self._call("status")

    async def async_manual_lamp(self) -> tuple[int]:
        """Fetch manual lamp level."""
        return await self._call("manual_lamp")

    async def async_set_manual_lamp(self, value: int) -> None:
        """Set manual lamp level."""
        await self._call("manual_lamp", [value])

    async def async_color_temperature(self) -> tuple[int]:
        """Fetch color temperature in hectoKelvin."""
        return await self._call("color_temperature")

    async def async_set_color_temperature(self, value_hk: int) -> None:
        """Set color temperature in hectoKelvin."""
        await self._call("color_temperature", [value_hk])

    async def async_ticker(self) -> tuple[Any, ...]:
        """Fetch ticker configuration."""
        return await self._call("ticker")

    async def async_set_ticker(self, data: list[Any]) -> None:
        """Set ticker configuration."""
        await self._call("ticker", data)

    async def async_send_raw(
        self,
        command: int,
        data: bytes = b"",
        subcommand: int | None = None,
    ) -> tuple[bool, tuple[int, ...], bytes]:
        """Send a raw MDC command and return (ack, response_cmd, response_data).

        This exposes the low-level MDC protocol so any command supported by the
        display can be issued, including ones not modelled by this integration.
        The checksum, header and display-id framing are handled by the library.
        """
        async with self._lock:
            cmd: int | tuple[int, int] = (
                command if subcommand is None else (command, subcommand)
            )
            try:
                return await self._client.send(cmd, self.display_id, data)
            except (
                MDCTimeoutError,
                MDCReadTimeoutError,
                MDCResponseError,
                OSError,
                ConnectionError,
            ):
                await self._reset_client()
                raise

    async def async_color_enhancement(self) -> bool | None:
        """Fetch the Color/Picture Enhancement state (raw MDC 0x21/0x50).

        Returns True/False, or None when the display doesn't report a value.
        """
        ack, _rcmd, data = await self.async_send_raw(
            ENHANCEMENT_CMD, b"", ENHANCEMENT_SUBCMD
        )
        if not ack or not data:
            return None
        return data[0] != ENHANCEMENT_OFF

    async def async_set_color_enhancement(self, on: bool) -> None:  # noqa: FBT001
        """Set the Color/Picture Enhancement state (raw MDC 0x21/0x50)."""
        value = ENHANCEMENT_ON if on else ENHANCEMENT_OFF
        await self.async_send_raw(ENHANCEMENT_CMD, bytes([value]), ENHANCEMENT_SUBCMD)

    async def async_device_name(self) -> tuple[Any, ...]:
        """Fetch device name."""
        return await self._call("device_name")

    async def async_serial_number(self) -> tuple[Any, ...]:
        """Fetch serial number."""
        return await self._call("serial_number")

    async def async_model_number(self) -> tuple[Any, ...]:
        """Fetch model number."""
        return await self._call("model_number")

    async def async_model_name(self) -> tuple[Any, ...]:
        """Fetch model name."""
        return await self._call("model_name")

    async def async_software_version(self) -> tuple[Any, ...]:
        """Fetch software version."""
        return await self._call("software_version")

    async def _call(self, command: str, data: list[Any] | None = None) -> Any:
        async with self._lock:
            last_error: BaseException | None = None
            for _attempt in range(2):
                try:
                    return await self._invoke(command, data)
                except (
                    MDCTimeoutError,
                    MDCReadTimeoutError,
                    MDCResponseError,
                    OSError,
                    ConnectionError,
                ) as err:
                    if self._should_ignore_error(command, data, err):
                        self._logger.debug(
                            "Ignoring MDC error for %s command; assuming success: %s",
                            command,
                            err,
                        )
                        await self._reset_client()
                        return None
                    last_error = err
                    await self._reset_client()
            if last_error is None:
                msg = "last_error not set after MDC retries"
                raise RuntimeError(msg)
            if self._should_ignore_error(command, data, last_error):
                self._logger.debug(
                    "Suppressing MDC error for %s command after retries: %s",
                    command,
                    last_error,
                )
                return None
            raise last_error

    async def _invoke(self, command: str, data: list[Any] | None) -> Any:
        method = getattr(self._client, command)
        if data is None:
            return await method(self.display_id)
        return await method(self.display_id, data)

    @staticmethod
    def _should_ignore_error(
        command: str, data: list[Any] | None, err: BaseException
    ) -> bool:
        """Return True when an MDC power command error should be treated as success."""
        return (
            command == "power"
            and data is not None
            and (
                (
                    isinstance(err, MDCResponseError)
                    and err.args
                    and err.args[0] == "Empty response"
                )
                or isinstance(err, ConnectionRefusedError)
                or (
                    isinstance(err, OSError)
                    and getattr(err, "errno", None) == CONNECTION_REFUSED_ERRNO
                )
            )
        )

    async def _reset_client(self) -> None:
        """Recreate MDC client after a connection failure."""
        try:
            if self._client.writer is not None:
                await self._client.close()
        finally:
            self._client = MDC(self._target, timeout=self._timeout, pin=self._pin)


class SamsungMDCDataUpdateCoordinator(DataUpdateCoordinator[SamsungMDCState]):
    """Coordinator to poll MDC device."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, device: SamsungMDCDevice
    ) -> None:
        """Initialize the update coordinator."""
        raw_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        update_interval: timedelta
        if isinstance(raw_interval, int):
            update_interval = timedelta(seconds=raw_interval)
        else:
            update_interval = raw_interval
        self._normal_update_interval = update_interval
        configured_display_id = entry.options.get(
            CONF_DISPLAY_ID, entry.data[CONF_DISPLAY_ID]
        )
        self._retry_update_interval = timedelta(seconds=30)
        self._in_retry_mode = False
        self._request_timeout = 8
        self._pending_power_on = False
        self._pending_power_expires: datetime | None = None
        self._last_status_success = False
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}-{configured_display_id}",
            update_interval=update_interval,
            config_entry=entry,
        )
        self.device = device

    async def _async_update_data(self) -> SamsungMDCState:  # noqa: PLR0912, PLR0915
        errors: list[BaseException] = []
        previous_state = self.data
        status_success = False

        async def _maybe_fetch(
            fetcher: Callable[[], Awaitable[Any]],
            description: str,
            fallback: Any,
            *,
            should_fetch: bool,
        ) -> Any:
            if not should_fetch:
                return fallback
            try:
                return await fetcher()
            except (
                MDCTimeoutError,
                MDCReadTimeoutError,
                MDCResponseError,
                NAKError,
                OSError,
                ConnectionError,
            ) as err:
                self.logger.debug(
                    "Using cached %s after MDC error: %s", description, err
                )
                return fallback

        try:
            async with timeout(self._request_timeout):
                for _attempt in range(3):
                    try:
                        status = await self.device.async_status()
                        status_success = True
                        if self._in_retry_mode:
                            self.update_interval = self._normal_update_interval
                            self._in_retry_mode = False
                        break
                    except (
                        MDCTimeoutError,
                        MDCReadTimeoutError,
                        MDCResponseError,
                        NAKError,
                        OSError,
                        ConnectionError,
                    ) as err:
                        errors.append(err)
                        await asyncio.sleep(0.5)
                else:
                    last_error = errors[-1]
                    if not self._in_retry_mode:
                        msg = (
                            "Transient MDC connection error after retries: %s; "
                            "retrying quickly"
                        )
                        self.logger.warning(msg, last_error)
                        self._in_retry_mode = True
                        self.update_interval = self._retry_update_interval
                    else:
                        self.logger.debug(
                            "Retrying MDC connection after error: %s", last_error
                        )
                    if previous_state is not None:
                        self._last_status_success = False
                        return previous_state
                    raise UpdateFailed(last_error) from last_error
        except TimeoutError as err:
            self.logger.warning(
                "MDC update exceeded %ss timeout; keeping last known state",
                self._request_timeout,
            )
            if previous_state is not None:
                self._last_status_success = False
                return previous_state
            raise UpdateFailed(err) from err
        self._last_status_success = status_success

        power_state, volume, mute_state, input_source, *_ = status
        self._pending_power_on_active()
        if power_state == commands.POWER.POWER_STATE.ON:
            self._clear_pending_power_on()
        parsed_volume = None if volume == UNKNOWN_VOLUME else int(volume)
        parsed_mute: commands.MUTE.MUTE_STATE | None
        if mute_state == commands.MUTE.MUTE_STATE.NONE:
            parsed_mute = None
        else:
            parsed_mute = mute_state
        parsed_source: commands.INPUT_SOURCE.INPUT_SOURCE_STATE | None
        if input_source == commands.INPUT_SOURCE.INPUT_SOURCE_STATE.NONE:
            parsed_source = None
        else:
            parsed_source = input_source

        should_poll_optional = (
            power_state != commands.POWER.POWER_STATE.OFF or previous_state is None
        )
        manual_lamp_value = (
            previous_state.manual_lamp if previous_state is not None else 0
        )
        manual_lamp = await _maybe_fetch(
            self.device.async_manual_lamp,
            "manual lamp level",
            (manual_lamp_value,),
            should_fetch=should_poll_optional,
        )
        color_temp_value = (
            previous_state.color_temperature_hk if previous_state is not None else 0
        )
        color_temp = await _maybe_fetch(
            self.device.async_color_temperature,
            "color temperature",
            (color_temp_value,),
            should_fetch=should_poll_optional,
        )
        ticker_value = previous_state.ticker if previous_state is not None else ()
        ticker = await _maybe_fetch(
            self.device.async_ticker,
            "ticker settings",
            ticker_value,
            should_fetch=should_poll_optional,
        )
        device_name = await _maybe_fetch(
            self.device.async_device_name,
            "device name",
            previous_state.device_name if previous_state is not None else None,
            should_fetch=should_poll_optional
            and (previous_state is None or previous_state.device_name is None),
        )
        serial_number = await _maybe_fetch(
            self.device.async_serial_number,
            "serial number",
            previous_state.serial_number if previous_state is not None else None,
            should_fetch=should_poll_optional
            and (previous_state is None or previous_state.serial_number is None),
        )
        model_name = await _maybe_fetch(
            self.device.async_model_name,
            "model name",
            previous_state.model_name if previous_state is not None else None,
            should_fetch=should_poll_optional
            and (previous_state is None or previous_state.model_name is None),
        )
        software_version = await _maybe_fetch(
            self.device.async_software_version,
            "software version",
            previous_state.software_version if previous_state is not None else None,
            should_fetch=should_poll_optional
            and (previous_state is None or previous_state.software_version is None),
        )
        enhancement_enabled = bool(
            self.config_entry.options.get(
                CONF_ENABLE_ENHANCEMENT,
                self.config_entry.data.get(
                    CONF_ENABLE_ENHANCEMENT, DEFAULT_ENABLE_ENHANCEMENT
                ),
            )
        )
        color_enhancement = await _maybe_fetch(
            self.device.async_color_enhancement,
            "color enhancement",
            previous_state.color_enhancement if previous_state is not None else None,
            should_fetch=should_poll_optional and enhancement_enabled,
        )

        return SamsungMDCState(
            power=power_state,
            volume=parsed_volume,
            mute=parsed_mute,
            input_source=parsed_source,
            manual_lamp=manual_lamp[0],
            color_temperature_hk=color_temp[0],
            ticker=ticker,
            device_name=_first_value(device_name),
            serial_number=_first_value(serial_number),
            model_name=_first_value(model_name),
            software_version=_first_value(software_version),
            color_enhancement=color_enhancement,
        )

    def mark_power_on_pending(self, duration_seconds: int = 45) -> None:
        """Mark that a power-on command was sent and wait for confirmation."""
        self._pending_power_on = True
        self._pending_power_expires = dt_util.utcnow() + timedelta(
            seconds=duration_seconds
        )

    @property
    def is_power_on_pending(self) -> bool:
        """Return True while a power-on command is pending."""
        return self._pending_power_on_active()

    def _pending_power_on_active(self) -> bool:
        """Return True while power-on is pending and not expired."""
        if not self._pending_power_on:
            return False
        if (
            self._pending_power_expires
            and dt_util.utcnow() > self._pending_power_expires
        ):
            self._clear_pending_power_on()
            return False
        return True

    def _clear_pending_power_on(self) -> None:
        """Clear pending power-on flag."""
        self._pending_power_on = False
        self._pending_power_expires = None

    @property
    def last_status_success(self) -> bool:
        """Return True when the most recent status poll succeeded."""
        return self._last_status_success

    @property
    def panel_state(self) -> PanelState:
        """Return the current panel state for UI consumption."""
        power_state = self.data.power if self.data is not None else None
        if power_state is None:
            return PanelState.STARTING if self.is_power_on_pending else PanelState.OFF
        if power_state == commands.POWER.POWER_STATE.ON:
            return PanelState.ON
        if self.is_power_on_pending:
            if not self._last_status_success:
                return PanelState.ON
            return PanelState.STARTING
        if power_state == commands.POWER.POWER_STATE.OFF:
            return PanelState.OFF
        return PanelState.STARTING


def _first_value(value: Any) -> Any | None:
    """Return first value from MDC response tuples."""
    if isinstance(value, (tuple, list)):
        return value[0] if value else None
    return value
