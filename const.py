"""Constants for the Flashforge Adventurer 5M integration.

Supports both Pro and non-Pro models.
"""

# Integration domain
DOMAIN = "flashforge_adventurer5m"

# Default settings
DEFAULT_SCAN_INTERVAL = 10  # seconds
DEFAULT_PRINTING_SCAN_INTERVAL = 2 # seconds
DEFAULT_PORT = 8898
DEFAULT_MCODE_PORT = 8899
DEFAULT_HOST = "printer.local"

# Configuration keys
CONF_PRINTING_SCAN_INTERVAL = "printing_scan_interval"

# Timeout settings (in seconds)
TIMEOUT_API_CALL = 10
TIMEOUT_COMMAND = 5
TIMEOUT_CONNECTION_TEST = 5

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
BACKOFF_FACTOR = 1.5

# API endpoints
ENDPOINT_DETAIL = "/detail"
# ENDPOINT_PAUSE = "/pause" # Removed, functionality moved to TCP M-code
# ENDPOINT_START = "/start" # Removed, functionality moved to TCP M-code
# ENDPOINT_CANCEL = "/cancel" # Removed, functionality moved to TCP M-code

# Printer states

# Status groups
PRINTING_STATES = ["BUILDING", "PRINTING", "RUNNING"]
ERROR_STATES = ["ERROR", "FAILED", "FATAL"]

# Door status
DOOR_OPEN = "OPEN"

# Light status
LIGHT_ON = "open"

# Binary sensor "on" states from API string values
AUTO_SHUTDOWN_ENABLED_STATE = "open"  # Based on API: autoShutdown: "open" / "close"
FAN_STATUS_ON_STATE = (
    "open"  # Based on API: externalFanStatus/internalFanStatus: "open" / "close"
)

# Connection states
CONNECTION_STATE_UNKNOWN = "unknown"
CONNECTION_STATE_CONNECTED = "connected"
CONNECTION_STATE_DISCONNECTED = "disconnected"

# Common error codes
ERROR_CODE_NONE = "0"

# Key attributes for validation
REQUIRED_RESPONSE_FIELDS = ["code", "message", "detail"]
REQUIRED_DETAIL_FIELDS = [
    "status",
    "ipAddr",
    "firmwareVersion",
    "doorStatus",
    "lightStatus",
]

# API Attribute Keys (used in binary_sensor.py, sensor.py, camera.py, etc.)
API_ATTR_STATUS = "status"
API_ATTR_ERROR_CODE = "errorCode"
API_ATTR_DOOR_STATUS = "doorStatus"
API_ATTR_LIGHT_STATUS = "lightStatus"
API_ATTR_AUTO_SHUTDOWN = "autoShutdown"
API_ATTR_EXTERNAL_FAN_STATUS = "externalFanStatus"
API_ATTR_INTERNAL_FAN_STATUS = "internalFanStatus"
API_ATTR_PRINT_FILE_NAME = "printFileName"
API_ATTR_PRINT_PROGRESS = "printProgress"
API_ATTR_PRINT_LAYER = "printLayer"
API_ATTR_TARGET_PRINT_LAYER = "targetPrintLayer"
API_ATTR_PRINT_DURATION = "printDuration"
API_ATTR_ESTIMATED_TIME = "estimatedTime"
API_ATTR_FIRMWARE_VERSION = "firmwareVersion"
API_ATTR_IP_ADDR = "ipAddr"
API_ATTR_CAMERA_STREAM_URL = "cameraStreamUrl"
API_ATTR_MODEL = "model"  # From camera.py device_info
API_ATTR_DETAIL = "detail"  # For accessing the nested detail object

# MJPEG Camera Settings
MJPEG_DEFAULT_PORT = 8080
MJPEG_STREAM_PATH = "/?action=stream"
MJPEG_DUMMY_URL = "http://0.0.0.0/"

# TCP Command Path Prefixes (for M23 start print command)
TCP_CMD_PRINT_FILE_PREFIX_USER = "0:/user/"
TCP_CMD_PRINT_FILE_PREFIX_ROOT = "0:/"

# Endstop Sensor Constants
# These API_ATTR keys are placeholders for how we'll store parsed M119 output in coordinator.data
API_ATTR_X_ENDSTOP_STATUS = "x_endstop_status"
API_ATTR_Y_ENDSTOP_STATUS = "y_endstop_status"
API_ATTR_Z_ENDSTOP_STATUS = "z_endstop_status"
API_ATTR_FILAMENT_ENDSTOP_STATUS = "filament_endstop_status"

# Endstop Sensor Names
NAME_X_ENDSTOP = "X Endstop"
NAME_Y_ENDSTOP = "Y Endstop"
NAME_Z_ENDSTOP = "Z Endstop"
NAME_FILAMENT_ENDSTOP = "Filament Sensor"

# Endstop Sensor Icons
ICON_X_ENDSTOP = "mdi:axis-x-arrow"
ICON_Y_ENDSTOP = "mdi:axis-y-arrow"
ICON_Z_ENDSTOP = "mdi:axis-z-arrow"
ICON_FILAMENT_ENDSTOP = "mdi:filament"

# Bed Leveling Sensor API Attribute Key
API_ATTR_BED_LEVELING_STATUS = "bed_leveling_status"

# Bed Leveling Sensor Name
NAME_BED_LEVELING = "Bed Leveling Active"

# Bed Leveling Sensor Icon
ICON_BED_LEVELING = "mdi:checkerboard" # Or mdi:format-list-bulleted-type

# Service Name Constants
# (It's better to import these from __init__.py if they are defined there,
# but if defined here, ensure they match __init__.py and services.yaml)
SERVICE_MOVE_RELATIVE = "move_relative"
