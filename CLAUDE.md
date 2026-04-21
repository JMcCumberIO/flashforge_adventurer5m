# CLAUDE.md — Flashforge Adventurer 5M Home Assistant Integration

This file provides guidance for AI assistants working on this codebase.

## Project Overview

This is a **Home Assistant custom integration** (`custom_component`) for the Flashforge Adventurer 5M and Adventurer 5M Pro 3D printers. It provides full monitoring and control through Home Assistant using two network interfaces:

| Interface | Port | Protocol | Purpose |
|-----------|------|----------|---------|
| HTTP REST API | 8898 | HTTP/JSON | Status polling, sensor data |
| M-code TCP | 8899 | Raw TCP | Printer control (G-code/M-code) |

**Domain:** `flashforge_adventurer5m`
**HA class:** `iot_class: local_polling`
**Python target:** 3.10+
**Key dependencies:** `aiohttp`, Home Assistant core libraries

---

## Repository Structure

```
flashforge_adventurer5m/
├── __init__.py          # Integration entry point: setup, service registration, teardown
├── coordinator.py       # DataUpdateCoordinator: HTTP polling + TCP command dispatch
├── const.py             # All constants (domain, ports, timeouts, API attribute keys, state lists)
├── config_flow.py       # HA config UI flow (setup + options) with connection validation
├── entity.py            # FlashforgeEntity: shared base class for all entities
├── flashforge_tcp.py    # FlashforgeTCPClient: low-level TCP M-code send/receive
├── sensor.py            # Sensor platform (30+ sensors from API detail object)
├── binary_sensor.py     # Binary sensor platform (printing, door, fan, endstops, bed leveling)
├── camera.py            # MJPEG camera platform (CoordinatorEntity + MjpegCamera)
├── number.py            # Number platform (extruder temp, bed temp, fan speed setpoint)
├── select.py            # Select platform (print file chooser)
├── button.py            # Button platform (pause, resume, cancel, home, filament change, bed level)
├── services.yaml        # HA service definitions with schemas and selectors
├── translations/
│   └── en.json          # English UI strings for config flow, entity names, services
├── manifest.json        # HA integration manifest (version, dependencies, IoT class)
├── .github/
│   ├── copilot-instructions.md   # GitHub Copilot-specific guidance
│   ├── workflows/
│   │   ├── tests.yml             # CI: style (Black/flake8), HACS, hassfest, test suite
│   │   └── bump-version.yml      # Version bump automation
│   └── pull_request_template.md
├── CONTRIBUTING.md      # Contribution guidelines + security policy
├── COVERAGE.md          # Test coverage documentation
├── REVIEW_CHANGES.md    # Recent code review improvements
└── README.md            # User-facing installation and usage guide
```

---

## Architecture

### Data Flow

```
Home Assistant
     │
     ▼
FlashforgeDataUpdateCoordinator  (coordinator.py)
     │                  │
     ▼                  ▼
HTTP GET/POST        FlashforgeTCPClient  (flashforge_tcp.py)
:8898/detail         :8899 (M-codes)
     │                  │
     ▼                  ▼
 coordinator.data    success, response_str
  {
    "code": 0,
    "message": "...",
    "detail": { status, temps, progress, ... },
    "printable_files": [...],    # injected from M20
    "x_position": float,         # injected from M114
    "y_position": float,
    "z_position": float,
    "x_endstop_status": bool,    # injected from M119
    "y_endstop_status": bool,
    "z_endstop_status": bool,
    "filament_endstop_status": bool,
    "bed_leveling_status": bool, # injected from G29 query
  }
     │
     ▼
Entities: sensor / binary_sensor / camera / number / select / button
```

### Coordinator Update Cycle

The coordinator (`FlashforgeDataUpdateCoordinator`) runs on two configurable intervals:
- **Regular interval** (default 10s): Used when printer is idle.
- **Printing interval** (default 2s): Automatically switches when `status` is in `PRINTING_STATES`.

Each cycle:
1. `async_update_data()` → HTTP POST to `:8898/detail` with `serialNumber` + `checkCode`
2. Parses JSON response, validates structure (lenient for non-Pro models)
3. Sends TCP M-codes to augment data: `M20` (list files), `M114` (position), `M119` (endstops)
4. Injects parsed results into the shared `coordinator.data` dict
5. All entities subscribed via `coordinator.async_add_listener(...)` are notified

### TCP Client (`FlashforgeTCPClient`)

- **Connect-send-close** pattern per command (no persistent connection).
- Commands must be prefixed with `~` and terminated with `\r\n` (e.g., `~M104 S210\r\n`).
- Waits for `ok\r\n` terminator in response.
- Returns `(success: bool, response: str)` tuple.
- All errors are caught and logged; never raises to caller.

---

## Key Conventions

### Constants (`const.py`)

All shared values live in `const.py`. Always import from there rather than using string/number literals. Key categories:

- **Ports:** `DEFAULT_PORT = 8898`, `DEFAULT_MCODE_PORT = 8899`
- **Timeouts:** `TIMEOUT_API_CALL`, `TIMEOUT_COMMAND`, `TIMEOUT_CONNECTION_TEST`
- **State groups:** `PRINTING_STATES`, `ERROR_STATES`, `IDLE_STATES`, `PAUSED_STATE`
- **API attribute keys:** `API_ATTR_STATUS`, `API_ATTR_PRINT_PROGRESS`, `API_ATTR_DOOR_STATUS`, etc.
- **Scan intervals:** `DEFAULT_SCAN_INTERVAL = 10`, `DEFAULT_PRINTING_SCAN_INTERVAL = 2`
- **Binary sensor "on" values:** `DOOR_OPEN = "OPEN"`, `LIGHT_ON = "open"`, `AUTO_SHUTDOWN_ENABLED_STATE = "open"`, `FAN_STATUS_ON_STATE = "open"`

> **Note:** `entity.py` imports `MANUFACTURER`, `DEVICE_MODEL_AD5M_PRO`, `DEVICE_NAME_DEFAULT`, `UNIQUE_ID_PREFIX`, `ATTR_TEMPERATURE`, `ATTR_SPEED`, and several `API_ATTR_*`/`MIN_*/MAX_*` constants that are not yet defined in `const.py`. When adding these constants, add them to `const.py`.

### Entity Base Class (`entity.py`)

`FlashforgeEntity(CoordinatorEntity[FlashforgeDataUpdateCoordinator])` provides:
- Standardized `_attr_name` = `f"{MANUFACTURER} {name_suffix}"`
- Standardized `_attr_unique_id` = `f"{UNIQUE_ID_PREFIX}{serial_number}_{unique_id_key}"`
- Shared `device_info` property (reads model + firmware from `coordinator.data["detail"]`)
- `async_added_to_hass()` registers the coordinator listener
- `_handle_coordinator_update()` calls `async_write_ha_state()`

**Subclasses should:**
1. Call `super().__init__(coordinator, name_suffix, unique_id_key)`
2. Override `_handle_coordinator_update()` to update internal state, then call `super()._handle_coordinator_update()`

### Data Access Pattern

```python
# Access top-level coordinator data:
value = self.coordinator.data.get("printable_files")

# Access printer detail object:
detail = self.coordinator.data.get("detail", {})
status = detail.get(API_ATTR_STATUS)  # e.g., "BUILDING", "IDLE"

# Endstop/bed leveling status (stored at root, not in "detail"):
x_triggered = self.coordinator.data.get(API_ATTR_X_ENDSTOP_STATUS)  # bool
```

### Device Info

All entities should group under the same HA device using:
```python
{
    "identifiers": {(DOMAIN, coordinator.serial_number)},
    "name": "Flashforge Adventurer 5M PRO",  # or use DEVICE_NAME_DEFAULT
    "manufacturer": "Flashforge",
    "model": "Adventurer 5M PRO",
    "sw_version": firmware_version,
}
```

---

## Platforms

### Sensors (`sensor.py`)
Defined via `SENSOR_DEFINITIONS` dict: `{api_key: (name, unit, device_class, state_class, is_top_level, is_percentage)}`. Sensors are only added if the data key exists in the first coordinator response. `printProgress` values are multiplied by 100 (API returns 0.0–1.0).

### Binary Sensors (`binary_sensor.py`)
Hardcoded list of `FlashforgeBinarySensor` instances. Endstop/bed leveling attributes come from the **root** of `coordinator.data` (not from `detail`). All others use `coordinator.data["detail"]`.

### Camera (`camera.py`)
`FlashforgeAdventurer5MCamera` extends both `CoordinatorEntity` and `MjpegCamera`. Stream URL priority: `cameraStreamUrl` from API → fallback `http://{ipAddr}:8080/?action=stream` → `MJPEG_DUMMY_URL`. Camera is `unavailable` when using the dummy URL.

### Number Entities (`number.py`)
Wraps `set_extruder_temperature`, `set_bed_temperature`, `set_fan_speed` services. Fan speed entity is `assumed_state=True` since the 0–255 setpoint cannot be read back from the API.

### Select Entity (`select.py`)
`FlashforgePrintFileSelect` shows files from `coordinator.data["printable_files"]` and calls `start_print` service on selection. Currently printing file is matched by suffix comparison.

### Button Entities (`button.py`)
Buttons use availability functions (`_is_printing`, `_is_paused`, `_is_idle`, `_is_printing_or_paused`) to enable/disable based on printer state.

---

## Services

All 24 services are registered in `async_setup_entry` in `__init__.py` and documented in `services.yaml`. Service constants are defined as `SERVICE_*` variables in `__init__.py`.

### Adding a New Service

1. Add `SERVICE_NEW_ACTION = "new_action"` constant in `__init__.py`
2. Add handler `async def handle_new_action(call: ServiceCall) -> None:` in `async_setup_entry`
3. Register: `hass.services.async_register(DOMAIN, SERVICE_NEW_ACTION, handle_new_action, schema=...)`
4. Add to the `all_service_names` list in `async_unload_entry`
5. Implement the method in `coordinator.py` (use `_send_tcp_command` helper)
6. Add service definition to `services.yaml`

### TCP Command Pattern in Coordinator

```python
async def new_action(self) -> bool:
    """Send M-code for new action."""
    command = f"~M999\r\n"
    action = "NEW ACTION description"
    success, response = await self._send_tcp_command(command, action)
    return success
```

---

## Adding New Sensors

1. Add `API_ATTR_NEW_KEY = "newApiKey"` to `const.py`
2. Add to `SENSOR_DEFINITIONS` in `sensor.py`:
   ```python
   "newApiKey": ("Human Name", unit, SensorDeviceClass.X, SensorStateClass.MEASUREMENT, False, False),
   ```
3. For binary sensors: add a `FlashforgeBinarySensor(...)` instance in `binary_sensor.py`'s `async_setup_entry`
4. Add icon/name constants to `const.py` for binary sensors
5. Update `translations/en.json` entity section

---

## Code Style

- **Formatter:** [Black](https://black.readthedocs.io/) — enforced in CI
- **Linter:** flake8 (errors only: E9, F63, F7, F82; max line length 127)
- **Type hints:** Required on all function parameters and return values
- **Docstrings:** Required on all public classes and methods (Google style Args/Returns)
- **Imports:** stdlib → third-party → homeassistant → local (relative)
- **Async:** All I/O operations must be `async`; use `asyncio.wait_for()` for timeouts
- **Logging:** Use module-level `_LOGGER = logging.getLogger(__name__)`; appropriate levels (DEBUG for verbose, WARNING for recoverable, ERROR for failures)

---

## Scan Intervals

| State | Interval | Source |
|-------|----------|--------|
| Idle | 10s (default) | `DEFAULT_SCAN_INTERVAL` |
| Printing | 2s (default) | `DEFAULT_PRINTING_SCAN_INTERVAL` |

Both are configurable via the HA options flow (scan_interval: 5–300s; printing_scan_interval: 1–15s).

---

## CI/CD Workflows

### `tests.yml` — runs on push/PR to main/master/dev

| Job | What it does |
|-----|-------------|
| `style` | Black check, flake8, manifest/services/translations validation |
| `validate` | HACS Action + hassfest validation |
| `test` | Full test suite on Python 3.10 + 3.11 with coverage upload |
| `performance` | Performance test suite (after `test`) |
| `stress` | Stress tests (scheduled weekly only) |

### Running Locally

```bash
pip install -r requirements_test.txt

# Style checks
black --check .
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Tests
python scripts/run_test_suite.py --config quick
python scripts/run_test_suite.py --config full --coverage
python scripts/analyze_coverage.py
```

---

## Security

**Never commit:**
- Real printer IP addresses, serial numbers, or check codes
- Network topology or firewall details
- Captured printer API responses with device identifiers

**Always use:**
- Mock/fake data in tests (`python scripts/generate_test_data.py`)
- `const.py` values for ports and paths — never hardcode
- Structured logging (`_LOGGER.debug/info/warning/error`) — never `print()`

---

## Connection & Troubleshooting Notes

| Symptom | Check |
|---------|-------|
| Cannot connect | Verify ports 8898 and 8899 are reachable; printer in LAN mode |
| Status/temp not updating | Review scan interval; confirm API response structure |
| Command failures | Confirm M-code has `~` prefix and `\r\n` suffix; check TCP response parsing |
| Non-Pro model issues | The integration uses **lenient validation** — succeeds if `detail.status` exists even when `code`/`message` are missing |

---

## Model Compatibility

The integration supports both **Adventurer 5M** and **Adventurer 5M Pro**. The config flow uses lenient response validation: if the standard `REQUIRED_RESPONSE_FIELDS` (`code`, `message`, `detail`) are absent but `detail.status` exists, setup succeeds. This accommodates non-Pro firmware that returns a minimal JSON structure.

---

## Important Inconsistencies to Be Aware Of

- `entity.py` imports constants (`MANUFACTURER`, `DEVICE_MODEL_AD5M_PRO`, `DEVICE_NAME_DEFAULT`, `UNIQUE_ID_PREFIX`, `ATTR_TEMPERATURE`, `ATTR_SPEED`, `MIN_*/MAX_*` values) that **may not exist** in `const.py` yet — `number.py`, `select.py`, and `button.py` also rely on some of these. Verify before using `entity.py`-based patterns.
- `sensor.py` and `binary_sensor.py` still use their own inline `device_info` dicts rather than inheriting from `FlashforgeEntity`. Prefer `FlashforgeEntity` for new entities.
- The `PLATFORMS` list in `__init__.py` only includes `["sensor", "camera", "binary_sensor"]` — `number`, `select`, and `button` are **not yet registered** there. Adding them requires updating `PLATFORMS` and the unload logic.
- `button.py` has a stray ` ``` ` at the end of the file — it is not valid Python and should be removed.
