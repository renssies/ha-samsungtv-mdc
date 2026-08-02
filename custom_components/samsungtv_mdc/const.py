"""Constants for the Samsung TV MDC integration."""

from datetime import timedelta
from enum import StrEnum

DOMAIN = "samsungtv_mdc"

CONF_DISPLAY_ID = "display_id"
CONF_PIN = "pin"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PORT = "port"
# Whether to create the "Color/Picture Enhancement" switch entity.
CONF_ENABLE_ENHANCEMENT = "enable_color_picture_enhancement"
DEFAULT_ENABLE_ENHANCEMENT = True

# "Color/Picture Enhancement" (official MDC name "Function: Picture Control -
# Color Enhancement"). Not modelled by python-samsung-mdc, so it is driven via
# the raw MDC send: command 0x21, sub-function 0x50, one on/off payload byte.
# GET: AA 21 <id> 01 50 <cs>; SET: AA 21 <id> 02 50 01/00 <cs>.
ENHANCEMENT_CMD = 0x21
ENHANCEMENT_SUBCMD = 0x50
ENHANCEMENT_ON = 0x01
ENHANCEMENT_OFF = 0x00
DEFAULT_PORT = 1515
DEFAULT_TIMEOUT = 3
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
MIN_SCAN_INTERVAL = timedelta(seconds=15)
MAX_SCAN_INTERVAL = timedelta(minutes=15)


class PanelState(StrEnum):
    """Display panel power states."""

    OFF = "off"
    STARTING = "starting"
    ON = "on"
