"""Switches for Samsung TV MDC."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from samsung_mdc import commands

from .const import CONF_ENABLE_ENHANCEMENT, DEFAULT_ENABLE_ENHANCEMENT
from .entity import SamsungMDCEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SamsungTVMDCConfigEntry
    from .coordinator import SamsungMDCDataUpdateCoordinator


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
    entities: list[SwitchEntity] = [SamsungMDCPowerSwitch(coordinator, device_id)]
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
    def is_on(self) -> bool:
        """Return True if the display is on (defaults to on when unavailable)."""
        if self.coordinator.data is None:
            return True
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


class SamsungMDCEnhancementSwitch(SamsungMDCEntity, SwitchEntity):
    """Switch to toggle the display's Color/Picture Enhancement.

    State is polled by the coordinator (raw MDC 0x21/0x50), so this is a normal
    toggle that reflects the display.
    """

    _attr_translation_key = "color_picture_enhancement"
    _attr_name = "Color/Picture Enhancement"

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize the enhancement switch."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-color-picture-enhancement"

    @property
    def is_on(self) -> bool:
        """Return True if enhancement is on (defaults to on when unavailable)."""
        if self.coordinator.data is None or self.coordinator.data.color_enhancement is None:
            return True
        return self.coordinator.data.color_enhancement

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable Color/Picture Enhancement."""
        await self.coordinator.device.async_set_color_enhancement(on=True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable Color/Picture Enhancement."""
        await self.coordinator.device.async_set_color_enhancement(on=False)
        await self.coordinator.async_request_refresh()
