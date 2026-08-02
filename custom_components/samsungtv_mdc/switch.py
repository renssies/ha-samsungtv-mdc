"""Switches for Samsung TV MDC."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError
from samsung_mdc import commands

from .const import CONF_ENABLE_ENHANCEMENT, DEFAULT_ENABLE_ENHANCEMENT
from .entity import SamsungMDCEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SamsungTVMDCConfigEntry
    from .coordinator import SamsungMDCDataUpdateCoordinator

# "Color/Picture Enhancement" (official MDC name: "Function: Picture Control -
# Color Enhancement"). It is not modelled by the python-samsung-mdc library, so
# it is driven via the raw MDC send: command 0x21, sub-function 0x50, with a
# single on/off payload byte (0x01 = on, 0x00 = off). The GET form is 0x21/0x50
# with no data; state is not read back (the switch is optimistic).
# Example for display id 8: SET ON = AA 21 08 02 50 01 7C, OFF = ...50 00 7B.
ENHANCEMENT_CMD: int | None = 0x21
ENHANCEMENT_SUBCMD: int | None = 0x50
ENHANCEMENT_ON_DATA = b"\x01"
ENHANCEMENT_OFF_DATA = b"\x00"


def _enhancement_enabled(entry: SamsungTVMDCConfigEntry) -> bool:
    """Return whether the Color/Picture Enhancement switch should be created."""
    return bool(
        entry.options.get(
            CONF_ENABLE_ENHANCEMENT,
            entry.data.get(CONF_ENABLE_ENHANCEMENT, DEFAULT_ENABLE_ENHANCEMENT),
        )
    )


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SamsungTVMDCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung MDC switches."""
    coordinator = entry.runtime_data.coordinator
    device_id = entry.runtime_data.device_id
    entities: list[SwitchEntity] = [
        SamsungMDCPowerSwitch(coordinator, device_id),
        SamsungMDCMuteSwitch(coordinator, device_id),
    ]
    if _enhancement_enabled(entry):
        entities.append(SamsungMDCEnhancementSwitch(coordinator, device_id))
    async_add_entities(entities)


class SamsungMDCPowerSwitch(SamsungMDCEntity, SwitchEntity):
    """Switch to control display power."""

    _attr_translation_key = "power"
    _attr_name = "Power"

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize the power switch."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-power"

    @property
    def is_on(self) -> bool | None:
        """Return True if the display is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.power == commands.POWER.POWER_STATE.ON

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the display on."""
        await self.coordinator.device.async_set_power(commands.POWER.POWER_STATE.ON)
        self.coordinator.mark_power_on_pending()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the display off."""
        await self.coordinator.device.async_set_power(commands.POWER.POWER_STATE.OFF)
        await self.coordinator.async_request_refresh()


class SamsungMDCMuteSwitch(SamsungMDCEntity, SwitchEntity):
    """Switch to control display mute."""

    _attr_translation_key = "mute"
    _attr_name = "Mute"

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize the mute switch."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-mute"

    @property
    def is_on(self) -> bool | None:
        """Return True if the display is muted."""
        if self.coordinator.data is None or self.coordinator.data.mute is None:
            return None
        return self.coordinator.data.mute == commands.MUTE.MUTE_STATE.ON

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Mute the display."""
        await self.coordinator.device.async_set_mute(muted=True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Unmute the display."""
        await self.coordinator.device.async_set_mute(muted=False)
        await self.coordinator.async_request_refresh()


class SamsungMDCEnhancementSwitch(SamsungMDCEntity, SwitchEntity):
    """Switch to toggle the display's Color/Picture Enhancement.

    The switch is optimistic (assumed state): the MDC command for this feature is
    not part of the modelled command set, so state is not read back.
    """

    _attr_translation_key = "color_picture_enhancement"
    _attr_name = "Color/Picture Enhancement"
    _attr_assumed_state = True

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize the enhancement switch."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-color-picture-enhancement"
        self._attr_is_on = False

    async def _async_send(self, data: bytes) -> None:
        """Send the raw enhancement command, guarding against an unset command."""
        if ENHANCEMENT_CMD is None:
            raise HomeAssistantError(
                translation_domain="samsungtv_mdc",
                translation_key="enhancement_not_configured",
            )
        await self.coordinator.device.async_send_raw(
            ENHANCEMENT_CMD, data, ENHANCEMENT_SUBCMD
        )

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable Color/Picture Enhancement."""
        await self._async_send(ENHANCEMENT_ON_DATA)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable Color/Picture Enhancement."""
        await self._async_send(ENHANCEMENT_OFF_DATA)
        self._attr_is_on = False
        self.async_write_ha_state()
