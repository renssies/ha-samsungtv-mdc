"""Base entity for Samsung TV MDC."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SamsungMDCDataUpdateCoordinator


class SamsungMDCEntity(CoordinatorEntity[SamsungMDCDataUpdateCoordinator]):
    """Common entity for Samsung MDC."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def available(self) -> bool:
        """Return True only when coordinator data is available.

        Entities become "unavailable" in Home Assistant whenever the coordinator
        is failing or has no data to report.
        """
        return super().available and self.coordinator.data is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        state = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="Samsung",
            name=(state.device_name if state else None)
            or f"Samsung MDC {self._device_id}",
            model=state.model_name if state else None,
            serial_number=state.serial_number if state else None,
            sw_version=state.software_version if state else None,
        )
