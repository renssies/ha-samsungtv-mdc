"""Buttons for Samsung TV MDC."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
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
            SamsungMDCRestartButton(coordinator, device_id),
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


class SamsungMDCRestartButton(SamsungMDCEntity, ButtonEntity):
    """Button to restart (reboot) the display."""

    _attr_translation_key = "restart"
    _attr_name = "Restart"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize restart button."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-restart"

    async def async_press(self) -> None:
        """Reboot the display via the MDC power command."""
        await self.coordinator.device.async_set_power(
            commands.POWER.POWER_STATE.REBOOT
        )
        await self.coordinator.async_request_refresh()
