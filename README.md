# Samsung TV MDC for Home Assistant

> 🍴 **Fork.** This is an extended fork of
> [gethnet/ha-samsungtv-mdc](https://github.com/gethnet/ha-samsungtv-mdc)
> (kept as the `upstream` git remote). Additions on top of upstream:
> - **Switch** entities: **Power**, **Mute**, and an optional **Color/Picture
>   Enhancement** switch (official MDC name "Function: Picture Control - Color
>   Enhancement"), which you can enable/disable from the config flow and options.
>   It is an optimistic switch driven by raw MDC command `0x21`/sub-function
>   `0x50` (not modelled by the library).
> - A **Restart** button (diagnostic entity category).
> - A **`samsungtv_mdc.send_raw`** action to send arbitrary/RAW MDC command bytes
>   (command + optional sub-command + hex data payload) to a display.
>
> See the shared [`../dev/`](../dev/README.md) Docker environment for running and
> debugging this integration alongside the other integrations in this workspace.

Custom integration for Samsung commercial displays that speak the MDC (Multiple Display Control) protocol. It uses the [`python-samsung-mdc`](https://pypi.org/project/python-samsung-mdc/) library to provide reliable power, input/source, volume/mute, backlight, color temperature, and ticker overlay control over TCP.

## AI/LLM Notice
Portions of this integration were authored with assistance from AI coding tools (LLMs) under human review. All generated content has been inspected, integrated, and tested for correctness and licensing compliance.

## Features
- Media Player entity (power, mute, volume set/step, input/source selection)
- Backlight (manual lamp) and color temperature number controls
- Ticker overlay helper (scrolling message on the display)
- Config Flow (no YAML) with optional TLS PIN for secured MDC
- Polling interval configurable per entry (5–15 minutes) with automatic reconnection after MDC timeouts

## Installation
### HACS (recommended)
1. In HACS, add this repository as a **Custom Repository** (category: Integration).
2. Install **Samsung TV MDC**.
3. Restart Home Assistant.
4. Add the integration via **Settings → Devices & Services → Add Integration → Samsung TV MDC**.

### Manual
1. Copy `custom_components/samsungtv_mdc` into your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.
3. Add the integration through the UI as above.

## Configuration
| Field | Description |
| --- | --- |
| Host | IP/hostname of the display (MDC TCP port 1515 by default) |
| Port | MDC port (default `1515`) |
| Display ID | MDC display ID (commonly `0` or `1`) |
| TLS PIN | Optional 4‑digit PIN if Secure MDC is enabled |
| Name | Friendly name for the entities |

### Options
- **Update interval** (minutes, 5–15)

## Services & Examples
- **Power and source**
```yaml
service: media_player.turn_on
target: {entity_id: media_player.lobby_display}
```

```yaml
service: media_player.select_source
target: {entity_id: media_player.lobby_display}
data: {source: "HDMI 2"}
```

- **Volume and mute**
```yaml
service: media_player.volume_set
target: {entity_id: media_player.lobby_display}
data: {volume_level: 0.35}
```

```yaml
service: media_player.mute_volume
target: {entity_id: media_player.lobby_display}
data: {is_volume_muted: true}
```

- **Ticker overlay**
```yaml
service: samsungtv_mdc.set_ticker
target: {entity_id: sensor.lobby_display_ticker}
data:
  message: "Meeting starts in 5 minutes"
  pos_horiz: left
  motion_on: true
  motion_dir: right
  motion_speed: slow
```

## Troubleshooting
- If commands stop working after power toggles, the integration automatically reconnects; wait a few seconds for the next poll or trigger `Reload` on the config entry.
- Ensure the display’s MDC port and display ID match your settings; some models default to display ID `1`.

## Breaking changes
- The legacy binary sensor `binary_sensor.<name>_power` has been removed. Use the new enum sensor `sensor.<name>_panel_state` (`on`, `starting`, `off`) for automations and dashboards.

## Development
- Create a venv and install test deps: `bash scripts/setup-dev.sh`
- Run tests: `source .venv/bin/activate && pytest`
- Lint with ruff: `source .venv/bin/activate && ruff check . > ruff.check.log`
- Apply auto fixes from ruff: `source .venv/bin/activate && ruff check . --fix > ruff.check.log`
- Install pre-commit hooks to lint before commits: `source .venv/bin/activate && pre-commit install`

## License
MIT License (see `LICENSE`).
