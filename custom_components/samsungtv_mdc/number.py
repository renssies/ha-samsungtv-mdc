"""Number entities for Samsung TV MDC."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberMode

from .entity import SamsungMDCEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SamsungTVMDCConfigEntry
    from .coordinator import SamsungMDCDataUpdateCoordinator, SamsungMDCDevice


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SamsungTVMDCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung MDC numbers."""
    coordinator = entry.runtime_data.coordinator
    device_id = entry.runtime_data.device_id
    async_add_entities(
        [
            SamsungMDCManualLampNumber(
                coordinator, device_id, entry.runtime_data.device
            ),
            SamsungMDCColorTemperatureNumber(
                coordinator, device_id, entry.runtime_data.device
            ),
        ]
    )


class _MDCBaseNumber(SamsungMDCEntity, NumberEntity):
    """Base number entity."""

    _attr_mode = NumberMode.BOX

    async def async_update(self) -> None:
        """Handle manual refresh."""
        await self.coordinator.async_request_refresh()


class SamsungMDCManualLampNumber(_MDCBaseNumber):
    """Number controlling manual lamp (backlight)."""

    _attr_translation_key = "manual_lamp"
    _attr_name = "Display backlight"
    _attr_icon = "mdi:brightness-6"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1

    def __init__(
        self,
        coordinator: SamsungMDCDataUpdateCoordinator,
        device_id: str,
        device: SamsungMDCDevice,
    ) -> None:
        """Initialize manual lamp number."""
        super().__init__(coordinator, device_id)
        self._device = device
        self._attr_unique_id = f"{device_id}-manual_lamp"

    @property
    def native_value(self) -> float | None:
        """Return current lamp level."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.manual_lamp

    async def async_set_native_value(self, value: float) -> None:
        """Set new lamp level."""
        await self._device.async_set_manual_lamp(int(value))
        await self.coordinator.async_request_refresh()


class SamsungMDCColorTemperatureNumber(_MDCBaseNumber):
    """Number controlling color temperature."""

    _attr_translation_key = "color_temperature"
    _attr_name = "Display color temperature"
    _attr_icon = "mdi:white-balance-sunny"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 28
    _attr_native_max_value = 168
    _attr_native_step = 1

    def __init__(
        self,
        coordinator: SamsungMDCDataUpdateCoordinator,
        device_id: str,
        device: SamsungMDCDevice,
    ) -> None:
        """Initialize color temperature number."""
        super().__init__(coordinator, device_id)
        self._device = device
        self._attr_unique_id = f"{device_id}-color_temperature"

    @property
    def native_value(self) -> float | None:
        """Return current color temperature in hectoKelvin."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.color_temperature_hk

    async def async_set_native_value(self, value: float) -> None:
        """Set new color temperature."""
        await self._device.async_set_color_temperature(int(value))
        await self.coordinator.async_request_refresh()
