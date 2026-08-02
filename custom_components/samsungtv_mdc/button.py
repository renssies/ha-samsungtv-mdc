"""Buttons for Samsung TV MDC."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
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
    """Set up Samsung MDC buttons."""
    coordinator = entry.runtime_data.coordinator
    device_id = entry.runtime_data.device_id
    async_add_entities(
        [
            SamsungMDCRefreshButton(coordinator, device_id),
            SamsungMDCPowerOnButton(coordinator, device_id),
            SamsungMDCPowerOffButton(coordinator, device_id),
            SamsungMDCVolumeUpButton(coordinator, device_id),
            SamsungMDCVolumeDownButton(coordinator, device_id),
        ]
    )


class SamsungMDCRefreshButton(SamsungMDCEntity, ButtonEntity):
    """Button to trigger immediate refresh."""

    _attr_translation_key = "refresh"
    _attr_name = "Refresh now"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize refresh button."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-refresh"

    async def async_press(self) -> None:
        """Request a data refresh."""
        await self.coordinator.async_request_refresh()


class SamsungMDCPowerOnButton(SamsungMDCEntity, ButtonEntity):
    """Button to power the display on."""

    _attr_translation_key = "power_on"
    _attr_name = "Power on"

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize power-on button."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-power-on"

    async def async_press(self) -> None:
        """Power the display on."""
        await self.coordinator.device.async_set_power(commands.POWER.POWER_STATE.ON)
        self.coordinator.mark_power_on_pending()
        await self.coordinator.async_request_refresh()


class SamsungMDCPowerOffButton(SamsungMDCEntity, ButtonEntity):
    """Button to power the display off."""

    _attr_translation_key = "power_off"
    _attr_name = "Power off"

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize power-off button."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-power-off"

    async def async_press(self) -> None:
        """Power the display off."""
        await self.coordinator.device.async_set_power(commands.POWER.POWER_STATE.OFF)
        await self.coordinator.async_request_refresh()


class SamsungMDCVolumeUpButton(SamsungMDCEntity, ButtonEntity):
    """Button to step the display volume up."""

    _attr_translation_key = "volume_up"
    _attr_name = "Volume up"

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize volume-up button."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-volume-up"

    async def async_press(self) -> None:
        """Step the volume up."""
        await self.coordinator.device.async_volume_step(
            commands.VOLUME_CHANGE.CHANGE_TO.UP
        )
        await self.coordinator.async_request_refresh()


class SamsungMDCVolumeDownButton(SamsungMDCEntity, ButtonEntity):
    """Button to step the display volume down."""

    _attr_translation_key = "volume_down"
    _attr_name = "Volume down"

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize volume-down button."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-volume-down"

    async def async_press(self) -> None:
        """Step the volume down."""
        await self.coordinator.device.async_volume_step(
            commands.VOLUME_CHANGE.CHANGE_TO.DOWN
        )
        await self.coordinator.async_request_refresh()
