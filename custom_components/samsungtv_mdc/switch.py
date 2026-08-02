"""Switches for Samsung TV MDC."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from samsung_mdc import commands

from .entity import SamsungMDCEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SamsungTVMDCConfigEntry
    from .coordinator import SamsungMDCDataUpdateCoordinator


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SamsungTVMDCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung MDC switches."""
    coordinator = entry.runtime_data.coordinator
    device_id = entry.runtime_data.device_id
    async_add_entities(
        [
            SamsungMDCPowerSwitch(coordinator, device_id),
            SamsungMDCMuteSwitch(coordinator, device_id),
        ]
    )


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
