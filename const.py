"""Constants for the Flashforge Adventurer 5M PRO integration."""
from typing import Dict # Add Dict import

# Integration domain
DOMAIN = "flashforge_adventurer5m"

# Manufacturer and Model
MANUFACTURER = "Flashforge"
DEVICE_MODEL_AD5M_PRO = "Adventurer 5M PRO" # Default model name
DEVICE_NAME_DEFAULT = f"{MANUFACTURER} {DEVICE_MODEL_AD5M_PRO}" # Full default device name for UI

# Default settings for connection, polling
DEFAULT_HOST = "printer.local"
DEFAULT_PORT = 8898  # HTTP API port
DEFAULT_MCODE_PORT = 8899  # TCP M-Code port
DEFAULT_SCAN_INTERVAL = 10  # seconds, for regular status updates
DEFAULT_PRINTING_SCAN_INTERVAL = 2  # seconds, when printer is printing
DEFAULT_UNKNOWN_SERIAL = "unknown" # Default for unknown serial number

# Configuration keys (used in config_flow.py, options_flow.py, __init__.py)
CONF_PRINTING_SCAN_INTERVAL = "printing_scan_interval" # Key for options flow

# Timeout settings (in seconds)
TIMEOUT_API_CALL = 10  # For general HTTP API calls in coordinator
TIMEOUT_COMMAND = 5    # For specific commands (used as COORDINATOR_COMMAND_TIMEOUT in coordinator)
TIMEOUT_CONNECTION_TEST = 5 # For connection test in config_flow
DEFAULT_TCP_TIMEOUT = 5 # Default timeout for TCP client operations in flashforge_tcp.py

# Retry settings (for config_flow connection test and coordinator HTTP calls)
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
BACKOFF_FACTOR = 1.5 # Factor to increase delay for subsequent retries

# API Endpoints
ENDPOINT_DETAIL = "/detail" # For fetching detailed printer status

# API Payload Keys (for HTTP POST requests)
API_KEY_SERIAL_NUMBER = "serialNumber"
API_KEY_CHECK_CODE = "checkCode"

# API Response Keys (expected in JSON responses)
API_KEY_CODE = "code"       # Typically 0 for success
API_KEY_MESSAGE = "message" # Response message

# API Response Values
API_VALUE_SUCCESS_CODE = 0 # Expected value of "code" field for successful operations

# Key attributes for API response validation
REQUIRED_RESPONSE_FIELDS = [API_KEY_CODE, API_KEY_MESSAGE, API_ATTR_DETAIL] # Updated to use constants
REQUIRED_DETAIL_FIELDS = [
    "status", # API_ATTR_STATUS
    "ipAddr", # API_ATTR_IP_ADDR
    "firmwareVersion", # API_ATTR_FIRMWARE_VERSION
    "doorStatus", # API_ATTR_DOOR_STATUS
    "lightStatus", # API_ATTR_LIGHT_STATUS
] # These are exact keys from the API `detail` object.

# Printer States (values for API_ATTR_STATUS)
PRINTING_STATES = ["BUILDING", "PRINTING", "RUNNING"] # States indicating active printing
PAUSED_STATE = "PAUSED" # State indicating paused print
IDLE_STATES = ["IDLE", "READY"] # States indicating printer is idle or ready, not actively printing/paused
ERROR_STATES = ["ERROR", "FAILED", "FATAL"] # States indicating an error condition

# Common states from API string values (often for binary sensors)
DOOR_OPEN = "OPEN"
LIGHT_ON = "open" # API uses "open" for light on, "close" for light off
AUTO_SHUTDOWN_ENABLED_STATE = "open"
FAN_STATUS_ON_STATE = "open"

# Connection States (internal state for coordinator)
CONNECTION_STATE_UNKNOWN = "unknown"
CONNECTION_STATE_CONNECTED = "connected"
CONNECTION_STATE_DISCONNECTED = "disconnected"

# Common Error Codes from API (value for API_ATTR_ERROR_CODE)
ERROR_CODE_NONE = "0" # Indicates no error

# API Attribute Keys (used to access specific fields in the API `detail` object or coordinator data)
# These should match the keys returned by the printer's HTTP API
API_ATTR_STATUS = "status"
API_ATTR_ERROR_CODE = "errorCode"
API_ATTR_DOOR_STATUS = "doorStatus"
API_ATTR_LIGHT_STATUS = "lightStatus"
API_ATTR_AUTO_SHUTDOWN = "autoShutdown" # e.g. "open" / "close"
API_ATTR_EXTERNAL_FAN_STATUS = "externalFanStatus" # e.g. "open" / "close"
API_ATTR_INTERNAL_FAN_STATUS = "internalFanStatus" # e.g. "open" / "close"
API_ATTR_PRINT_FILE_NAME = "printFileName"
API_ATTR_PRINT_PROGRESS = "printProgress" # e.g. "0.50" for 50%
API_ATTR_PRINT_LAYER = "printLayer"
API_ATTR_TARGET_PRINT_LAYER = "targetPrintLayer"
API_ATTR_PRINT_DURATION = "printDuration" # in seconds
API_ATTR_ESTIMATED_TIME = "estimatedTime" # in seconds (remaining)
API_ATTR_FIRMWARE_VERSION = "firmwareVersion"
API_ATTR_IP_ADDR = "ipAddr"
API_ATTR_CAMERA_STREAM_URL = "cameraStreamUrl"
API_ATTR_MODEL = "model" # Printer model as reported by API
API_ATTR_DETAIL = "detail"  # Key for the nested detail object in API response

# API Attribute Keys for Endstop Status (parsed from M119, stored in coordinator.data)
API_ATTR_X_ENDSTOP_STATUS = "x_endstop_status"
API_ATTR_Y_ENDSTOP_STATUS = "y_endstop_status"
API_ATTR_Z_ENDSTOP_STATUS = "z_endstop_status"
API_ATTR_FILAMENT_ENDSTOP_STATUS = "filament_endstop_status"

# API Attribute Key for Bed Leveling Status (parsed from M420, stored in coordinator.data)
API_ATTR_BED_LEVELING_STATUS = "bed_leveling_status"

# API Attribute Keys for Chamber and Extruder Temperatures (from API detail or other sources)
API_ATTR_CHAMBER_TEMP = "chamberTemp"
API_ATTR_CHAMBER_TARGET_TEMP = "chamberTargetTemp"
API_ATTR_LEFT_TEMP = "leftTemp"
# API_ATTR_LEFT_TARGET_TEMP is defined below
API_ATTR_RIGHT_TEMP = "rightTemp"
# API_ATTR_RIGHT_TARGET_TEMP is defined below
API_ATTR_PLAT_TEMP = "platTemp"
# API_ATTR_PLAT_TARGET_TEMP is defined below

# API Attribute Keys for Filament and Print Statistics (from API detail or other sources)
API_ATTR_CUMULATIVE_FILAMENT = "cumulativeFilament"
API_ATTR_CUMULATIVE_PRINT_TIME = "cumulativePrintTime"
API_ATTR_FILL_AMOUNT = "fillAmount" # This might be chamber humidity based on some context
API_ATTR_LEFT_FILAMENT_TYPE = "leftFilamentType"
API_ATTR_RIGHT_FILAMENT_TYPE = "rightFilamentType"
API_ATTR_ESTIMATED_LEFT_LEN = "estimatedLeftLen"
API_ATTR_ESTIMATED_LEFT_WEIGHT = "estimatedLeftWeight"
API_ATTR_ESTIMATED_RIGHT_LEN = "estimatedRightLen"
API_ATTR_ESTIMATED_RIGHT_WEIGHT = "estimatedRightWeight"

# API Attribute Keys for Fan Speeds (from API detail or other sources)
API_ATTR_CHAMBER_FAN_SPEED = "chamberFanSpeed" # RPM or percentage? Assuming RPM for now
API_ATTR_COOLING_FAN_SPEED_RPM = "coolingFanSpeed" # Actual RPM of the part cooling fan

# API Attribute Keys for Environmental Sensors (from API detail or other sources)
API_ATTR_TVOC = "tvoc" # Total Volatile Organic Compounds

# API Attribute Keys for System Information (from API detail or other sources)
API_ATTR_REMAINING_DISK_SPACE = "remainingDiskSpace"
API_ATTR_Z_AXIS_COMPENSATION = "zAxisCompensation"
API_ATTR_AUTO_SHUTDOWN_TIME = "autoShutdownTime" # In minutes or seconds?
API_ATTR_CURRENT_PRINT_SPEED = "currentPrintSpeed" # Percentage or mm/s?
API_ATTR_FLASH_REGISTER_CODE = "flashRegisterCode"
API_ATTR_LOCATION = "location"
API_ATTR_MAC_ADDR = "macAddr"
API_ATTR_MEASURE = "measure" # Purpose unclear, might be related to some sensor reading
API_ATTR_NOZZLE_COUNT = "nozzleCnt"
API_ATTR_NOZZLE_MODEL = "nozzleModel"
API_ATTR_NOZZLE_STYLE = "nozzleStyle"
API_ATTR_PID = "pid" # Product ID or Process ID?
API_ATTR_POLAR_REGISTER_CODE = "polarRegisterCode"
API_ATTR_PRINT_SPEED_ADJUST = "printSpeedAdjust" # Percentage for print speed override

# API Attribute Key for Coordinator-added Data (not directly from API)
API_ATTR_PRINTABLE_FILES = "printable_files" # Key for list of printable files in coordinator data

# API Attribute Keys for Coordinate data (parsed from M114, stored in coordinator.data)
API_ATTR_X_POSITION = "x_position"
API_ATTR_Y_POSITION = "y_position"
API_ATTR_Z_POSITION = "z_position"

# API Attribute Keys for Target Temperatures (from API detail object)
API_ATTR_LEFT_TARGET_TEMP = "leftTargetTemp"
API_ATTR_RIGHT_TARGET_TEMP = "rightTargetTemp" # If dual extruder support is added
API_ATTR_PLAT_TARGET_TEMP = "platTargetTemp"
# API_ATTR_COOLING_FAN_SPEED = "coolingFanSpeed" # This is actual RPM, not setpoint 0-255

# MJPEG Camera Settings
MJPEG_DEFAULT_PORT = 8080
MJPEG_STREAM_PATH = "/?action=stream"
MJPEG_DUMMY_URL = "http://0.0.0.0/" # Dummy URL for unavailable camera

# TCP M-Code Command Settings
TCP_RESPONSE_TERMINATOR_OK = "ok\r\n"
ENCODING_UTF8 = "utf-8"

# TCP M-Code Command Strings
TCP_CMD_PAUSE_PRINT = "~M25\r\n"
TCP_CMD_RESUME_PRINT = "~M24\r\n"
TCP_CMD_CANCEL_PRINT = "~M26\r\n"
TCP_CMD_GET_ENDSTOPS = "~M119\r\n"
TCP_CMD_GET_POSITION = "~M114\r\n"
TCP_CMD_GET_BED_LEVEL_STATUS = "~M420 S0\r\n" # Get bed leveling state
TCP_CMD_LIST_FILES_M661 = "~M661\r\n" # Alternative to M20 for file listing, seems to provide full paths
TCP_CMD_LIST_FILES_M20 = "~M20\r\n"   # Standard G-code for listing SD card files
TCP_CMD_LIGHT_ON_TEMPLATE = "~M146 r255 g255 b255 F0\r\n" # F0 for chamber light?
TCP_CMD_LIGHT_OFF = "~M146 r0 g0 b0 F0\r\n"
TCP_CMD_EXTRUDER_TEMP_TEMPLATE = "~M104 S{temperature}\r\n"
TCP_CMD_BED_TEMP_TEMPLATE = "~M140 S{temperature}\r\n"
TCP_CMD_FAN_SPEED_TEMPLATE = "~M106 S{speed}\r\n"
TCP_CMD_FAN_OFF = "~M107\r\n"
TCP_CMD_MOVE_AXIS_TEMPLATE = "~G0" # Base for G0 move, add X,Y,Z,F as needed
TCP_CMD_RELATIVE_POSITIONING = "~G91\r\n"
TCP_CMD_ABSOLUTE_POSITIONING = "~G90\r\n"
TCP_CMD_DELETE_FILE_TEMPLATE = "~M30 {file_path}\r\n"
TCP_CMD_DISABLE_STEPPERS = "~M18\r\n"
TCP_CMD_ENABLE_STEPPERS = "~M17\r\n"
TCP_CMD_SPEED_PERCENTAGE_TEMPLATE = "~M220 S{percentage}\r\n"
TCP_CMD_FLOW_PERCENTAGE_TEMPLATE = "~M221 S{percentage}\r\n"
TCP_CMD_HOME_AXES_TEMPLATE = "~G28" # Add axes like X, Y, Z or empty for all
TCP_CMD_FILAMENT_CHANGE = "~M600\r\n"
TCP_CMD_EMERGENCY_STOP = "~M112\r\n"
TCP_CMD_REPORT_FIRMWARE_CAPS = "~M115\r\n"
TCP_CMD_PLAY_BEEP_TEMPLATE = "~M300 S{pitch} P{duration}\r\n"
TCP_CMD_START_BED_LEVELING = "~G29\r\n"
TCP_CMD_SAVE_SETTINGS_EEPROM = "~M500\r\n"
TCP_CMD_READ_SETTINGS_EEPROM = "~M501\r\n"
TCP_CMD_RESTORE_FACTORY_SETTINGS = "~M502\r\n"
TCP_CMD_START_PRINT_TEMPLATE = "~M23 {file_path}\r\n" # Template for M23 (select file to print)

# TCP Command Path Prefixes (for M23 start print command, M30 delete file)
TCP_CMD_PRINT_FILE_PREFIX_USER = "0:/user/"
TCP_CMD_PRINT_FILE_PREFIX_ROOT = "0:/" # For paths like /data/.. becomes 0:/data/...
TCP_CMD_M661_PATH_PREFIX = "/data/" # File paths from M661 start with this

# M661 File List Parsing
M661_SEPARATOR = "::\x00\x00\x00"
M661_CMD_PREFIX = "CMD M661 Received.\r\ok\r\n" # Note: original had a typo here, fixed ok
M661_FILE_EXT_GCODE = ".gcode"
M661_FILE_EXT_GX = ".gx"

# Validation Limits for Service Calls
MIN_EXTRUDER_TEMP = 0
MAX_EXTRUDER_TEMP = 300 # Example, adjust if needed
MIN_BED_TEMP = 0
MAX_BED_TEMP = 120    # Example, adjust if needed
MIN_FAN_SPEED = 0
MAX_FAN_SPEED = 255
MIN_SPEED_PERCENTAGE = 10 # Example
MAX_SPEED_PERCENTAGE = 500 # Example
MIN_FLOW_PERCENTAGE = 50 # Example
MAX_FLOW_PERCENTAGE = 200 # Example
MIN_BEEP_PITCH = 0
MAX_BEEP_PITCH = 10000 # Hz
MIN_BEEP_DURATION = 0
MAX_BEEP_DURATION = 10000 # ms

# Internal unique ID prefix
UNIQUE_ID_PREFIX = "flashforge_"

# Sensor / Entity names, icons (already in const.py, just ensuring they are reviewed)
# NAME_X_ENDSTOP, ICON_X_ENDSTOP etc. are fine.
# NAME_BED_LEVELING, ICON_BED_LEVELING are fine.

# Buffer size for TCP client
TCP_BUFFER_SIZE = 1024

# Default entity name for the camera in Home Assistant UI (if not overridden)
CAMERA_DEFAULT_NAME_SUFFIX = "Camera"
CAMERA_UI_NAME = f"{MANUFACTURER} {DEVICE_MODEL_AD5M_PRO} Camera"

# Service names are defined in __init__.py and services.yaml
# No need to duplicate all service string names here unless used across multiple modules
# from const.py directly.

# Service to move printer axes by a relative amount.
SERVICE_MOVE_RELATIVE = "move_relative"

# Generic G-code Service
SERVICE_SEND_GCODE = "send_gcode"
ATTR_GCODE = "gcode"

# Note: API_ATTR_MODEL is "model", DEVICE_MODEL_AD5M_PRO is "Adventurer 5M PRO"
# The first is the API key, the second is a specific string value.
# DEVICE_NAME_DEFAULT uses MANUFACTURER and DEVICE_MODEL_AD5M_PRO.
# In entity.py, device_info model uses: detail.get(API_ATTR_MODEL, DEVICE_MODEL_AD5M_PRO)
# This means it tries to get the model from API, if not found, defaults to "Adventurer 5M PRO".
# This is a good approach.


# Service Names
SERVICE_PAUSE_PRINT = "pause_print"
SERVICE_START_PRINT = "start_print"
SERVICE_CANCEL_PRINT = "cancel_print"
SERVICE_TOGGLE_LIGHT = "toggle_light"
SERVICE_RESUME_PRINT = "resume_print"
SERVICE_SET_EXTRUDER_TEMPERATURE = "set_extruder_temperature"
SERVICE_SET_BED_TEMPERATURE = "set_bed_temperature"
SERVICE_SET_FAN_SPEED = "set_fan_speed"
SERVICE_TURN_FAN_OFF = "turn_fan_off"
SERVICE_MOVE_AXIS = "move_axis"
SERVICE_DELETE_FILE = "delete_file"
SERVICE_DISABLE_STEPPERS = "disable_steppers"
SERVICE_ENABLE_STEPPERS = "enable_steppers"
SERVICE_SET_SPEED_PERCENTAGE = "set_speed_percentage"
SERVICE_SET_FLOW_PERCENTAGE = "set_flow_percentage"
SERVICE_HOME_AXES = "home_axes"
SERVICE_EMERGENCY_STOP = "emergency_stop"
SERVICE_LIST_FILES = "list_files"
SERVICE_REPORT_FIRMWARE_CAPABILITIES = "report_firmware_capabilities"
SERVICE_PLAY_BEEP = "play_beep"
SERVICE_START_BED_LEVELING = "start_bed_leveling"
SERVICE_SAVE_SETTINGS_TO_EEPROM = "save_settings_to_eeprom"
SERVICE_READ_SETTINGS_FROM_EEPROM = "read_settings_from_eeprom"
SERVICE_FILAMENT_CHANGE = "filament_change"
SERVICE_RESTORE_FACTORY_SETTINGS = "restore_factory_settings"
# SERVICE_MOVE_RELATIVE is already defined below
# SERVICE_SEND_GCODE is already defined below

# Service Attributes
ATTR_FILE_PATH = "file_path"
ATTR_PERCENTAGE = "percentage"
ATTR_HOME_X = "x"
ATTR_HOME_Y = "y"
ATTR_HOME_Z = "z"
ATTR_TEMPERATURE = "temperature"
ATTR_SPEED = "speed"
# ATTR_GCODE is already defined below


# Mapping of error codes to human-readable descriptions
# This dictionary should be populated with known error codes and their meanings.
# Example: ERROR_CODE_DESCRIPTIONS = {"1": "Nozzle temperature error", "2": "Bed temperature error"}
ERROR_CODE_DESCRIPTIONS: Dict[str, str] = {}
