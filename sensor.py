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
    UnitOfTime,
    UnitOfInformation,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from typing import Dict, Any  # Import Dict and Any for type hinting
from .const import DOMAIN
from .coordinator import FlashforgeDataUpdateCoordinator
from .entity import FlashforgeEntity

_LOGGER = logging.getLogger(__name__)

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
        "µg/m³",
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
        "mm/s",
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
        True,
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
        value_exists = False
        if is_top_level and attribute_key in coordinator.data:
            value_exists = True
        elif (
            not is_top_level
            and coordinator.data.get("detail")
            and attribute_key in coordinator.data["detail"]
        ):
            value_exists = True
        if value_exists:
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
