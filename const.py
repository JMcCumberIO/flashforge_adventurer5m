"""Constants for the Flashforge Adventurer 5M PRO integration."""

# Integration domain
DOMAIN = "flashforge_adventurer5m"

# Default settings
DEFAULT_SCAN_INTERVAL = 10  # seconds
DEFAULT_PORT = 8898
DEFAULT_MCODE_PORT = 8899
DEFAULT_HOST = "printer.local"

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
ENDPOINT_COMMAND = "/command" # Retained for potential other HTTP commands

# Printer states
STATE_IDLE = "IDLE"
STATE_PRINTING = "PRINTING"
STATE_PAUSED = "PAUSED"
STATE_ERROR = "ERROR"
STATE_MAINTAINING = "MAINTAINING"
STATE_BUSY = "BUSY"

# Status groups
PRINTING_STATES = ["BUILDING", "PRINTING", "RUNNING"]
ERROR_STATES = ["ERROR", "FAILED", "FATAL"]
BUSY_STATES = ["MAINTAINING", "BUSY", "PREPARING"]

# Door status
DOOR_OPEN = "OPEN"
DOOR_CLOSED = "CLOSED"

# Light status
LIGHT_ON = "open"
LIGHT_OFF = "OFF"

# Binary sensor "on" states from API string values
AUTO_SHUTDOWN_ENABLED_STATE = "open" # Based on API: autoShutdown: "open" / "close"
FAN_STATUS_ON_STATE = "open"         # Based on API: externalFanStatus/internalFanStatus: "open" / "close"

# Connection states
CONNECTION_STATE_UNKNOWN = "unknown"
CONNECTION_STATE_CONNECTED = "connected"
CONNECTION_STATE_DISCONNECTED = "disconnected"
CONNECTION_STATE_AUTHENTICATING = "authenticating"

# Common error codes
ERROR_CODE_NONE = "0"
ERROR_CODE_AUTH_FAILED = "401"
ERROR_CODE_NOT_FOUND = "404"
ERROR_CODE_CONNECTION_FAILED = "connection_failed"
ERROR_CODE_TIMEOUT = "timeout"
ERROR_CODE_INVALID_RESPONSE = "invalid_response"

# Key attributes for validation
REQUIRED_RESPONSE_FIELDS = ["code", "message", "detail"]
REQUIRED_DETAIL_FIELDS = [
    "status",
    "ipAddr",
    "firmwareVersion",
    "doorStatus",
    "lightStatus"
]

# Units
UNIT_TEMP_CELSIUS = "°C"
UNIT_PROGRESS_PERCENT = "%"
UNIT_LENGTH_MM = "mm"
UNIT_WEIGHT_G = "g"
UNIT_TIME_SEC = "s"
