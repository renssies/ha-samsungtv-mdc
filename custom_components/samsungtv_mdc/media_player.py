"""Media player entity for Samsung TV MDC."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from samsung_mdc import commands

from .entity import SamsungMDCEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SamsungTVMDCConfigEntry
    from .coordinator import SamsungMDCDataUpdateCoordinator, SamsungMDCDevice

SUPPORTED_SOURCES: dict[commands.INPUT_SOURCE.INPUT_SOURCE_STATE, str] = {
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI1: "HDMI 1",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI2: "HDMI 2",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI3: "HDMI 3",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI4: "HDMI 4",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.DISPLAY_PORT_1: "DisplayPort 1",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.DISPLAY_PORT_2: "DisplayPort 2",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.DISPLAY_PORT_3: "DisplayPort 3",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.PC: "PC",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.DVI: "DVI",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.COMPONENT: "Component",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.AV: "AV",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.AV2: "AV 2",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.MAGIC_INFO: "MagicInfo",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.TV_DTV: "TV/DTV",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.INTERNAL_USB: "Internal USB",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.URL_LAUNCHER: "URL Launcher",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.REMOTE_WORKSPACE: "Remote Workspace",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.WEB_BROWSER: "Web Browser",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.IWB: "Interactive Whiteboard",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HD_BASE_T: "HDBaseT",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.OCM: "OCM",
    commands.INPUT_SOURCE.INPUT_SOURCE_STATE.MEDIA_MAGIC_INFO_S: "MagicInfo S",
}

SOURCE_NAME_LOOKUP = {
    name.lower(): enum_value for enum_value, name in SUPPORTED_SOURCES.items()
}

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SamsungTVMDCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung MDC media player."""
    runtime = entry.runtime_data
    async_add_entities(
        [SamsungMDCMediaPlayer(runtime.coordinator, runtime.device_id, runtime.device)]
    )


class SamsungMDCMediaPlayer(SamsungMDCEntity, MediaPlayerEntity):
    """Representation of a Samsung MDC display."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = SUPPORTED_FEATURES
    _attr_translation_key = "display"
    _attr_name = "Display"

    def __init__(
        self,
        coordinator: SamsungMDCDataUpdateCoordinator,
        device_id: str,
        device: SamsungMDCDevice,
    ) -> None:
        """Initialize media player entity."""
        super().__init__(coordinator, device_id)
        self._device = device
        self._attr_unique_id = f"{device_id}-media_player"
        self._turn_on_status = "Initializing display"

    @property
    def state(self) -> MediaPlayerState | None:
        """Return media player state."""
        if self.coordinator.data is None:
            return None
        power = self.coordinator.data.power
        if power == commands.POWER.POWER_STATE.ON:
            return MediaPlayerState.ON
        if (
            power == commands.POWER.POWER_STATE.OFF
            and self.coordinator.is_power_on_pending
        ):
            return MediaPlayerState.ON
        if power == commands.POWER.POWER_STATE.OFF:
            return MediaPlayerState.OFF
        return None

    @property
    def volume_level(self) -> float | None:
        """Return the volume level (0..1)."""
        if self.coordinator.data is None:
            return None
        volume = self.coordinator.data.volume
        if volume is None:
            return None
        return volume / 100

    @property
    def is_volume_muted(self) -> bool | None:
        """Return whether the device is muted."""
        if self.coordinator.data is None:
            return None
        mute_state = self.coordinator.data.mute
        if mute_state is None:
            return None
        return mute_state == commands.MUTE.MUTE_STATE.ON

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        if self.coordinator.data is None:
            return None
        current = self.coordinator.data.input_source
        if current is None:
            return None
        if current in SUPPORTED_SOURCES:
            return SUPPORTED_SOURCES[current]
        if hasattr(current, "name"):
            return current.name.replace("_", " ").title()
        return str(current)

    @property
    def source_list(self) -> list[str]:
        """Return the list of available input sources."""
        return list(SUPPORTED_SOURCES.values())

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return additional state attributes."""
        if self.coordinator.is_power_on_pending:
            return {"status": self._turn_on_status}
        return {}

    async def async_turn_on(self) -> None:
        """Turn on the display."""
        self.coordinator.mark_power_on_pending()
        await self._device.async_set_power(commands.POWER.POWER_STATE.ON)
        await self._refresh()

    async def async_turn_off(self) -> None:
        """Turn off the display."""
        await self._device.async_set_power(commands.POWER.POWER_STATE.OFF)
        await self._refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0..1)."""
        volume_int = max(0, min(100, int(volume * 100)))
        await self._device.async_set_volume(volume_int)
        await self._refresh()

    async def async_volume_up(self) -> None:
        """Increase volume by one step."""
        await self._device.async_volume_step(commands.VOLUME_CHANGE.CHANGE_TO.UP)
        await self._refresh()

    async def async_volume_down(self) -> None:
        """Decrease volume by one step."""
        await self._device.async_volume_step(commands.VOLUME_CHANGE.CHANGE_TO.DOWN)
        await self._refresh()

    async def async_mute_volume(self, mute: bool) -> None:  # noqa: FBT001
        """Mute or unmute the display."""
        await self._device.async_set_mute(mute)
        await self._refresh()

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        source_enum = SOURCE_NAME_LOOKUP.get(source.lower())
        if source_enum is None:
            return
        await self._device.async_set_input_source(source_enum)
        await self._refresh()

    async def async_update(self) -> None:
        """Request an update from the coordinator."""
        await self._refresh()

    async def _refresh(self) -> None:
        """Trigger a coordinator refresh."""
        await self.coordinator.async_request_refresh()
