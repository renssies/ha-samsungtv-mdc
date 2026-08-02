"""Sensor and text entities for Samsung TV MDC."""

from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.text import TextEntity
from samsung_mdc import commands

from .const import PanelState
from .entity import SamsungMDCEntity

TICKER_FIELD_COUNT = 14

# All selectable input sources (the NONE placeholder is reported as "unknown").
INPUT_SOURCE_OPTIONS: list[str] = [
    source.name.lower()
    for source in commands.INPUT_SOURCE.INPUT_SOURCE_STATE
    if source is not commands.INPUT_SOURCE.INPUT_SOURCE_STATE.NONE
]

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
    """Set up Samsung MDC text entities."""
    coordinator = entry.runtime_data.coordinator
    device_id = entry.runtime_data.device_id
    async_add_entities(
        [
            SamsungMDCPanelStateSensor(coordinator, device_id),
            SamsungMDCInputSourceSensor(coordinator, device_id),
            SamsungMDCTickerMessageText(
                coordinator,
                device_id,
                entry.runtime_data.device,
            ),
        ]
    )


class SamsungMDCPanelStateSensor(SamsungMDCEntity, SensorEntity):
    """Enum sensor reporting the display panel state."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "panel_state"
    _attr_name = "Panel state"
    _attr_icon = "mdi:television"
    _attr_options: ClassVar[list[str]] = [state.value for state in PanelState]

    def __init__(
        self,
        coordinator: SamsungMDCDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize panel state sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-panel-state"

    @property
    def native_value(self) -> str:
        """Return the panel state."""
        return self.coordinator.panel_state.value


class SamsungMDCInputSourceSensor(SamsungMDCEntity, SensorEntity):
    """Enum sensor reporting the display's current input source."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "input_source"
    _attr_name = "Source"
    _attr_icon = "mdi:video-input-hdmi"
    _attr_options: ClassVar[list[str]] = INPUT_SOURCE_OPTIONS

    def __init__(
        self,
        coordinator: SamsungMDCDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize input source sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-input-source"

    @property
    def native_value(self) -> str | None:
        """Return the current input source, or None when unknown/off."""
        if self.coordinator.data is None:
            return None
        source = self.coordinator.data.input_source
        if source is None:
            return None
        return source.name.lower()


class SamsungMDCTickerMessageText(SamsungMDCEntity, TextEntity):
    """Text entity to update ticker message."""

    _attr_translation_key = "ticker_message"
    _attr_name = "Ticker message"
    _attr_min_length = 0
    _attr_max_length = 300

    def __init__(
        self,
        coordinator: SamsungMDCDataUpdateCoordinator,
        device_id: str,
        device: SamsungMDCDevice,
    ) -> None:
        """Initialize ticker message text entity."""
        super().__init__(coordinator, device_id)
        self._device = device
        self._attr_unique_id = f"{device_id}-ticker-message"

    @property
    def native_value(self) -> str | None:
        """Return current ticker message."""
        ticker = self.coordinator.data.ticker
        if not ticker:
            return None
        return str(ticker[-1])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose ticker configuration details."""
        ticker = self.coordinator.data.ticker
        if not ticker:
            return {
                "enabled": None,
                "start_time": None,
                "end_time": None,
                "position_horizontal": None,
                "position_vertical": None,
                "motion_enabled": None,
                "motion_direction": None,
                "motion_speed": None,
                "font_size": None,
                "foreground_color": None,
                "background_color": None,
                "foreground_opacity": None,
                "background_opacity": None,
                "message_length": None,
            }

        (
            on_off,
            start_time,
            end_time,
            pos_horiz,
            pos_verti,
            motion_on,
            motion_dir,
            motion_speed,
            font_size,
            foreground_color,
            background_color,
            foreground_opacity,
            background_opacity,
            message,
        ) = ticker

        def _enum_value(value: Any) -> Any:
            return value.name.lower() if hasattr(value, "name") else value

        def _time_value(value: Any) -> Any:
            if isinstance(value, time):
                return value.strftime("%H:%M")
            return value

        return {
            "enabled": bool(on_off),
            "start_time": _time_value(start_time),
            "end_time": _time_value(end_time),
            "position_horizontal": _enum_value(pos_horiz),
            "position_vertical": _enum_value(pos_verti),
            "motion_enabled": bool(motion_on),
            "motion_direction": _enum_value(motion_dir),
            "motion_speed": _enum_value(motion_speed),
            "font_size": _enum_value(font_size),
            "foreground_color": _enum_value(foreground_color),
            "background_color": _enum_value(background_color),
            "foreground_opacity": _enum_value(foreground_opacity),
            "background_opacity": _enum_value(background_opacity),
            "message_length": len(str(message)),
        }

    async def async_set_value(self, value: str) -> None:
        """Update ticker message while preserving existing ticker config."""
        ticker = self.coordinator.data.ticker
        if not ticker:
            ticker = await self._device.async_ticker()
        data = list(ticker)
        if len(data) < TICKER_FIELD_COUNT:
            return
        data[13] = value
        await self._device.async_set_ticker(data)
        await self.coordinator.async_request_refresh()
