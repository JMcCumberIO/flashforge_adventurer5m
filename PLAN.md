# PLAN.md — Flashforge Adventurer 5M Integration: Prioritized Improvement Plan

## Overview

Prioritized by severity: **P1** = blocking/crash bug, **P2** = correctness/behavioural bug, **P3** = cleanup/consistency.

---

## P1-A: Add missing constants to `const.py` (Blocking ImportError)

### Problem

Multiple platform files import constants from `const.py` that do not exist, causing `ImportError` on startup and preventing entire platforms from loading.

| Missing constant | Imported by |
|---|---|
| `MANUFACTURER`, `DEVICE_MODEL_AD5M_PRO`, `DEVICE_NAME_DEFAULT`, `UNIQUE_ID_PREFIX` | `entity.py` |
| `ATTR_TEMPERATURE`, `ATTR_SPEED`, `API_ATTR_LEFT_TARGET_TEMP`, `API_ATTR_PLAT_TARGET_TEMP`, `MIN/MAX_EXTRUDER_TEMP`, `MIN/MAX_BED_TEMP`, `MIN/MAX_FAN_SPEED` | `number.py` |
| `SERVICE_PAUSE_PRINT`, `SERVICE_RESUME_PRINT`, `SERVICE_CANCEL_PRINT`, `SERVICE_HOME_AXES`, `SERVICE_FILAMENT_CHANGE`, `SERVICE_START_BED_LEVELING`, `PAUSED_STATE`, `IDLE_STATES` | `button.py` |
| `SERVICE_START_PRINT`, `ATTR_FILE_PATH` | `select.py` |

### Files to change

- `const.py` — append all missing constants

### Constants to add

```python
# Device identity (entity.py)
MANUFACTURER = "Flashforge"
DEVICE_MODEL_AD5M_PRO = "Adventurer 5M PRO"
DEVICE_NAME_DEFAULT = "Flashforge Adventurer 5M PRO"
UNIQUE_ID_PREFIX = "flashforge_"

# State groups (button.py)
PAUSED_STATE = "PAUSED"
IDLE_STATES = ["IDLE", "READY"]

# API attribute keys (number.py)
API_ATTR_LEFT_TARGET_TEMP = "leftTargetTemp"
API_ATTR_PLAT_TARGET_TEMP = "platTargetTemp"

# Number entity ranges (number.py)
MIN_EXTRUDER_TEMP = 0.0
MAX_EXTRUDER_TEMP = 300.0
MIN_BED_TEMP = 0.0
MAX_BED_TEMP = 120.0
MIN_FAN_SPEED = 0.0
MAX_FAN_SPEED = 255.0

# Service call attribute keys (number.py, select.py)
ATTR_TEMPERATURE = "temperature"
ATTR_SPEED = "speed"
ATTR_FILE_PATH = "file_path"

# Service names (button.py, select.py) — consolidate from __init__.py
SERVICE_PAUSE_PRINT = "pause_print"
SERVICE_RESUME_PRINT = "resume_print"
SERVICE_CANCEL_PRINT = "cancel_print"
SERVICE_HOME_AXES = "home_axes"
SERVICE_FILAMENT_CHANGE = "filament_change"
SERVICE_START_BED_LEVELING = "start_bed_leveling"
SERVICE_START_PRINT = "start_print"
```

---

## P1-B: Remove stray backtick from `button.py` (SyntaxError)

### Problem

`button.py` line 214 contains a bare ` ``` `. Python raises `SyntaxError` on import, so the entire button platform fails to load.

### Files to change

- `button.py` — delete line 214 (the line containing only ` ``` `)

---

## P1-C: Add `number`, `select`, `button` to `PLATFORMS` in `__init__.py`

### Problem

`PLATFORMS = ["sensor", "camera", "binary_sensor"]` omits three platforms. Additionally, `async_forward_entry_setups` uses a hardcoded literal list (also missing those three) instead of the `PLATFORMS` constant. These platforms are never registered; none of their entities appear in Home Assistant.

### Files to change

- `__init__.py`

### Exact changes

```python
# Line 57
PLATFORMS = ["sensor", "camera", "binary_sensor", "number", "select", "button"]

# Lines 106–108 — use the constant, not a literal list
await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
```

`async_unload_entry` already uses `PLATFORMS` correctly — no change needed there.

---

## P2-A: Fix double coordinator-listener registration in `FlashforgeEntity`

### Problem

`entity.py`'s `async_added_to_hass` calls `await super().async_added_to_hass()` (which already registers a listener via `CoordinatorEntity`) **and** also manually registers a second listener via `coordinator.async_add_listener`. This causes `_handle_coordinator_update` and `async_write_ha_state` to fire twice per update cycle for every `FlashforgeEntity` subclass.

It also calls `_handle_coordinator_update()` directly on line 61 before the entity is fully set up, which triggers a premature `async_write_ha_state`.

### Files to change

- `entity.py`

### Exact change

```python
async def async_added_to_hass(self) -> None:
    """When entity is added to hass."""
    await super().async_added_to_hass()
    # CoordinatorEntity.async_added_to_hass handles listener registration internally.
```

Remove lines 57–61 (manual `async_add_listener` and manual `_handle_coordinator_update()` call).

---

## P2-B: Refactor `FlashforgeSensor` to inherit `FlashforgeEntity`

### Problem

`FlashforgeSensor` extends `CoordinatorEntity` directly and builds its own `device_info` dict inline (hardcoding `"Adventurer 5M PRO"` as name and model, using a plain `dict` instead of `DeviceInfo`). It also manually updates `sw_version` in `_handle_coordinator_update`, which is unnecessary since `FlashforgeEntity.device_info` is a property that re-reads coordinator data on every call.

### Files to change

- `sensor.py`

### Changes needed

1. Change class declaration to `class FlashforgeSensor(FlashforgeEntity, SensorEntity):`
2. Update `__init__` to call `super().__init__(coordinator, name_suffix=name, unique_id_key=attribute_key)` — remove manual `_attr_name` and `_attr_unique_id` assignments.
3. Remove inline `_attr_device_info` dict construction and the `sw_version` update in `_handle_coordinator_update`.
4. Remove the redundant `async_added_to_hass` override (lines 437–442) — handled by `FlashforgeEntity` after the P2-A fix.

---

## P2-C: Refactor `FlashforgeBinarySensor` to inherit `FlashforgeEntity`

### Problem

Same inline `device_info` dict issue as `FlashforgeSensor`. Additionally, `async_added_to_hass` does **not** call `await super().async_added_to_hass()`, skipping `CoordinatorEntity`'s own setup (cancellation registration, etc.) — this is a correctness bug.

### Files to change

- `binary_sensor.py`

### Changes needed

1. Change class declaration to `class FlashforgeBinarySensor(FlashforgeEntity, BinarySensorEntity):`
2. Update `__init__` to call `super().__init__(coordinator, name_suffix=name, unique_id_key=sensor_key)`.
3. Remove inline `device_info` property.
4. Fix `async_added_to_hass` to call `await super().async_added_to_hass()`.

> **Note:** The endstop/bed-leveling sensors use a hardcoded allowlist in `is_on` to decide root vs. `detail` lookup (lines 334–341). Consider adding an `is_top_level: bool = False` constructor parameter to make this general rather than keeping a hardcoded list.

---

## P2-D: Fix wrong `SensorDeviceClass` on print progress sensor

### Problem

`sensor.py` assigns `SensorDeviceClass.BATTERY` to the `printProgress` sensor. This causes HA to display it with battery-specific UI. The correct choice for a generic percentage progress value is `None`.

### Files to change

- `sensor.py`

### Exact change

In `SENSOR_DEFINITIONS`, for the `"printProgress"` entry, change the device_class from `SensorDeviceClass.BATTERY` to `None`.

---

## P3-A: Remove duplicate `SERVICE_MOVE_RELATIVE` constant

### Problem

`SERVICE_MOVE_RELATIVE = "move_relative"` is defined in both `const.py` (line 131) and `__init__.py` (line 53). Diverging definitions would cause silent bugs.

### Files to change

- `__init__.py` — remove the duplicate definition; import from `.const` instead.

---

## P3-B: Consolidate all `SERVICE_*` constants from `__init__.py` into `const.py`

### Problem

Service name constants are defined in `__init__.py`, but `button.py` and `select.py` import from `.const`. This is the root cause that forced P1-A's duplication. Long-term fix is to move all `SERVICE_*` definitions to `const.py` and import them in `__init__.py` from `.const`.

### Files to change

- `const.py` — add all service name constants (already done as part of P1-A)
- `__init__.py` — remove `SERVICE_*` definitions on lines 26–53; replace with `from .const import SERVICE_PAUSE_PRINT, ...`

---

## P3-C: Add type annotations to `sensor.py`'s `async_setup_entry`

### Problem

```python
async def async_setup_entry(hass, entry, async_add_entities):  # no annotations
```

All other platform files include proper type annotations. Required by code style.

### Files to change

- `sensor.py`

### Exact change

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
```

Add corresponding imports: `HomeAssistant`, `ConfigEntry`, `AddEntitiesCallback`.

---

## Implementation Order

| Step | Item | Why this order |
|------|------|----------------|
| 1 | P1-B | Trivial syntax fix; unblocks all other checks |
| 2 | P1-A + P3-B | Add constants and consolidate service names in one pass |
| 3 | P1-C | Enable the three missing platforms |
| 4 | P2-A | Fix base class before refactoring subclasses |
| 5 | P2-B | Refactor sensor after base class is correct |
| 6 | P2-C | Refactor binary_sensor after base class is correct |
| 7 | P2-D | Quick one-line fix to sensor device class |
| 8 | P3-A | Subsumed by P3-B; remove last duplicate |
| 9 | P3-C | Type annotation cleanup |

After each step: `black --check . && flake8 . --count --select=E9,F63,F7,F82`
