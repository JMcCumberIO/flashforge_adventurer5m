import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfMass,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTime,
    UnitOfInformation,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from typing import Dict, Any, Optional  # Import Dict, Any, Optional for type hinting
from .const import DOMAIN
from .coordinator import FlashforgeDataUpdateCoordinator
from .entity import FlashforgeEntity

_LOGGER = logging.getLogger(__name__)

# Suggested display units for duration sensors whose native/API unit reads
# awkwardly at typical magnitudes (e.g. a multi-hour print duration shown in
# raw seconds). The native unit stays the accurate, unconverted API value so
# history graphs and long-term statistics remain valid; only the *displayed*
# unit changes, which Home Assistant converts automatically since these are
# all UnitOfTime values. Sensors not listed here keep suggested == native.
SENSOR_SUGGESTED_UNIT_OVERRIDES = {
    "printDuration": UnitOfTime.MINUTES,
    "estimatedTime": UnitOfTime.MINUTES,
    "cumulativePrintTime": UnitOfTime.HOURS,
}

# Centralized sensor definitions: key: (name, unit, device_class, state_class, is_top_level, is_percentage)
SENSOR_DEFINITIONS = {
    # Top-Level
    "code": ("Status Code", None, None, SensorStateClass.MEASUREMENT, True, False),
    "message": ("Status Message", None, None, None, True, False),
    # Detail section
    "status": ("Status", None, None, None, False, False),
    "firmwareVersion": ("Firmware Version", None, None, None, False, False),
    "chamberTemp": (
        "Chamber Temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "chamberTargetTemp": (
        "Chamber Target Temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "leftTemp": (
        "Left Nozzle Temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "leftTargetTemp": (
        "Left Nozzle Target Temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "rightTemp": (
        "Right Nozzle Temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "rightTargetTemp": (
        "Right Nozzle Target Temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "platTemp": (
        "Platform Temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "platTargetTemp": (
        "Platform Target Temperature",
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "printProgress": (
        "Print Progress",
        PERCENTAGE,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        True,
    ),
    "printDuration": (
        "Print Duration",
        UnitOfTime.SECONDS,
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "estimatedTime": (
        "Estimated Time Remaining",
        UnitOfTime.SECONDS,
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "cumulativeFilament": (
        "Cumulative Filament",
        UnitOfLength.METERS,
        SensorDeviceClass.DISTANCE,
        SensorStateClass.TOTAL_INCREASING,
        False,
        False,
    ),
    "cumulativePrintTime": (
        "Cumulative Print Time",
        UnitOfTime.MINUTES,
        SensorDeviceClass.DURATION,
        SensorStateClass.TOTAL_INCREASING,
        False,
        False,
    ),
    "fillAmount": (
        "Fill Amount",
        None,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "leftFilamentType": ("Left Filament Type", None, None, None, False, False),
    "rightFilamentType": ("Right Filament Type", None, None, None, False, False),
    "estimatedLeftLen": (
        "Estimated Left Length",
        UnitOfLength.MILLIMETERS,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "estimatedLeftWeight": (
        "Estimated Left Weight",
        UnitOfMass.GRAMS,
        SensorDeviceClass.WEIGHT,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "estimatedRightLen": (
        "Estimated Right Length",
        UnitOfLength.MILLIMETERS,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "estimatedRightWeight": (
        "Estimated Right Weight",
        UnitOfMass.GRAMS,
        SensorDeviceClass.WEIGHT,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "chamberFanSpeed": (
        "Chamber Fan Speed",
        REVOLUTIONS_PER_MINUTE,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "coolingFanSpeed": (
        "Cooling Fan Speed",
        REVOLUTIONS_PER_MINUTE,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    # "externalFanStatus": ("External Fan Status", None, None, None, False, False), # Replaced by binary_sensor
    # "internalFanStatus": ("Internal Fan Status", None, None, None, False, False), # Replaced by binary_sensor
    "tvoc": (
        "TVOC",
        CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "remainingDiskSpace": (
        "Remaining Disk Space",
        UnitOfInformation.GIGABYTES,
        SensorDeviceClass.DATA_SIZE,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "zAxisCompensation": (
        "Z Axis Compensation",
        UnitOfLength.MILLIMETERS,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    # Add more as needed...
    # "autoShutdown": ("Auto Shutdown Status", None, None, None, False, False), # Replaced by binary_sensor
    "autoShutdownTime": (
        "Auto Shutdown Time",
        UnitOfTime.MINUTES,
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "currentPrintSpeed": (
        "Current Print Speed",
        UnitOfSpeed.MILLIMETERS_PER_SECOND,
        SensorDeviceClass.SPEED,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "flashRegisterCode": ("Flash Register Code", None, None, None, False, False),
    "location": ("Location", None, None, None, False, False),
    "macAddr": ("MAC Address", None, None, None, False, False),
    "measure": ("Build Volume", None, None, None, False, False),
    "nozzleCnt": (
        "Nozzle Count",
        None,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    "nozzleModel": ("Nozzle Model", None, None, None, False, False),
    "nozzleStyle": (
        "Nozzle Style",
        None,
        None,
        None,
        False,
        False,
    ),  # Changed state_class to None
    "pid": ("Printer ID (PID)", None, None, None, False, False),
    "polarRegisterCode": ("Polar Register Code", None, None, None, False, False),
    "printSpeedAdjust": (
        "Print Speed Adjustment",
        PERCENTAGE,
        None,
        SensorStateClass.MEASUREMENT,
        False,
        False,  # already a whole-number %, not a 0-1 fraction
    ),
    "printable_files": (
        "Printable Files Count",
        "files",
        None,
        SensorStateClass.MEASUREMENT,
        True,
        False,
    ),
    "x_position": (
        "X Position",
        UnitOfLength.MILLIMETERS,
        None,
        SensorStateClass.MEASUREMENT,
        True,
        False,
    ),
    "y_position": (
        "Y Position",
        UnitOfLength.MILLIMETERS,
        None,
        SensorStateClass.MEASUREMENT,
        True,
        False,
    ),
    "z_position": (
        "Z Position",
        UnitOfLength.MILLIMETERS,
        None,
        SensorStateClass.MEASUREMENT,
        True,
        False,
    ),
}


# Adaptive, human-readable duration sensors companion to the numeric ones
# above: (source_attribute_key, name, unique_id_key, is_top_level, seconds_per_unit).
# seconds_per_unit normalizes the source API value to seconds before
# formatting, since printDuration/estimatedTime are already in seconds but
# cumulativePrintTime is in minutes.
FRIENDLY_DURATION_SENSORS = [
    ("printDuration", "Print Duration (Friendly)", "print_duration_friendly", False, 1),
    (
        "estimatedTime",
        "Estimated Time Remaining (Friendly)",
        "estimated_time_remaining_friendly",
        False,
        1,
    ),
    (
        "cumulativePrintTime",
        "Cumulative Print Time (Friendly)",
        "cumulative_print_time_friendly",
        False,
        60,
    ),
]


def _format_duration_adaptive(total_seconds: Any) -> Optional[str]:
    """Format a duration in seconds as an adaptive, human-readable string.

    Scales from seconds to minutes to hours to days, showing the two most
    significant units at whichever scale the value falls into, e.g. "45s",
    "12m 30s", "2h 15m", "1d 3h".
    """
    if total_seconds is None:
        return None
    try:
        total_seconds = max(0, int(round(float(total_seconds))))
    except (ValueError, TypeError):
        return None

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _source_value_exists(
    coordinator: FlashforgeDataUpdateCoordinator, attribute_key: str, is_top_level: bool
) -> bool:
    """Check whether the coordinator currently has data for a given API key."""
    if is_top_level:
        return attribute_key in coordinator.data
    return (
        bool(coordinator.data.get("detail"))
        and attribute_key in coordinator.data["detail"]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Flashforge sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors_to_add = []

    for attribute_key, (
        name,
        unit,
        device_class,
        state_class,
        is_top_level,
        is_percentage,
    ) in SENSOR_DEFINITIONS.items():
        if _source_value_exists(coordinator, attribute_key, is_top_level):
            sensors_to_add.append(
                FlashforgeSensor(
                    coordinator,
                    attribute_key,
                    name,
                    unit,
                    device_class,
                    state_class,
                    is_top_level,
                    is_percentage,
                )
            )
        else:
            _LOGGER.debug(f"Skipping sensor {attribute_key}, no data found.")

    for (
        attribute_key,
        name,
        unique_id_key,
        is_top_level,
        seconds_per_unit,
    ) in FRIENDLY_DURATION_SENSORS:
        if _source_value_exists(coordinator, attribute_key, is_top_level):
            sensors_to_add.append(
                FlashforgeFriendlyDurationSensor(
                    coordinator,
                    attribute_key,
                    name,
                    unique_id_key,
                    is_top_level,
                    seconds_per_unit,
                )
            )
        else:
            _LOGGER.debug(
                f"Skipping friendly duration sensor {attribute_key}, no data found."
            )

    if sensors_to_add:
        async_add_entities(sensors_to_add)


class FlashforgeSensor(FlashforgeEntity, SensorEntity):
    """A sensor for one JSON field from the printer."""

    def __init__(
        self,
        coordinator: FlashforgeDataUpdateCoordinator,
        attribute_key: str,
        name: str,
        unit,
        device_class,
        state_class,
        is_top_level: bool,
        is_percentage: bool,
    ):
        super().__init__(coordinator, name_suffix=name, unique_id_key=attribute_key)
        self._attribute_key = attribute_key
        self._is_top_level = is_top_level
        self._is_percentage = is_percentage

        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = PERCENTAGE if is_percentage else unit
        self._attr_suggested_unit_of_measurement = (
            PERCENTAGE
            if is_percentage
            else SENSOR_SUGGESTED_UNIT_OVERRIDES.get(attribute_key, unit)
        )
        self._attr_extra_state_attributes: Dict[str, Any] = {}
        self._attr_native_value: Any = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = self.coordinator.last_update_success
        raw_value = None
        if self.coordinator.data:
            if self._is_top_level:
                raw_value = self.coordinator.data.get(self._attribute_key)
            elif self.coordinator.data.get("detail"):
                raw_value = self.coordinator.data.get("detail", {}).get(
                    self._attribute_key
                )

        if self._attribute_key == "printable_files":
            files_list = raw_value if isinstance(raw_value, list) else []
            self._attr_native_value = len(files_list)
            self._attr_extra_state_attributes["files"] = files_list
        elif self._is_percentage and raw_value is not None:
            try:
                self._attr_native_value = round(float(raw_value) * 100.0, 1)
            except (ValueError, TypeError) as e:
                _LOGGER.warning(
                    "Could not convert value '%s' to percentage for sensor %s (%s). Error: %s",
                    raw_value,
                    self._attribute_key,
                    self.name,
                    e,
                    exc_info=True,
                )
                self._attr_native_value = None
        else:
            self._attr_native_value = raw_value

        self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self._attr_native_value


class FlashforgeFriendlyDurationSensor(FlashforgeEntity, SensorEntity):
    """Adaptive human-readable duration sensor, e.g. "2h 15m" or "1d 3h".

    Companion to the numeric duration sensor for the same source value. This
    entity has no device_class or unit -- it's a formatted string, not a
    statistics-friendly number -- so the numeric sensor remains the source of
    truth for history graphs, long-term statistics, and automations.
    """

    _attr_icon = "mdi:timer-outline"

    def __init__(
        self,
        coordinator: FlashforgeDataUpdateCoordinator,
        attribute_key: str,
        name: str,
        unique_id_key: str,
        is_top_level: bool,
        seconds_per_unit: int,
    ):
        super().__init__(coordinator, name_suffix=name, unique_id_key=unique_id_key)
        self._attribute_key = attribute_key
        self._is_top_level = is_top_level
        self._seconds_per_unit = seconds_per_unit
        self._attr_native_value: Optional[str] = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = self.coordinator.last_update_success
        raw_value = None
        if self.coordinator.data:
            if self._is_top_level:
                raw_value = self.coordinator.data.get(self._attribute_key)
            elif self.coordinator.data.get("detail"):
                raw_value = self.coordinator.data.get("detail", {}).get(
                    self._attribute_key
                )

        total_seconds = None
        if raw_value is not None:
            try:
                total_seconds = float(raw_value) * self._seconds_per_unit
            except (ValueError, TypeError):
                total_seconds = None

        self._attr_native_value = _format_duration_adaptive(total_seconds)
        self.async_write_ha_state()

    @property
    def native_value(self) -> Optional[str]:
        """Return the formatted duration string."""
        return self._attr_native_value
