"""Sensor platform for Flashforge Adventurer 5M PRO integration."""
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfMass,
    UnitOfLength,
    UnitOfTime,
    UnitOfInformation,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
)
from typing import Dict, Any, Optional, List, Tuple # Import Dict, Any, Optional, List, Tuple
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
# CoordinatorEntity is now inherited via FlashforgeEntity
from .entity import FlashforgeEntity # Import the base class
from .const import (
    DOMAIN,
    API_ATTR_FIRMWARE_VERSION,
    API_ATTR_STATUS,
    API_ATTR_PRINT_PROGRESS,
    API_ATTR_PRINT_DURATION,
    API_ATTR_ESTIMATED_TIME,
    API_KEY_CODE,
    API_KEY_MESSAGE,
    API_ATTR_X_POSITION, # For X coordinate sensor
    API_ATTR_Y_POSITION, # For Y coordinate sensor
    API_ATTR_Z_POSITION, # For Z coordinate sensor
    # TODO: Define and import other API_ATTR_* constants for remaining string keys in SENSOR_DEFINITIONS
    # For keys in "detail" object that are not covered by specific API_ATTR_*
    # For now, I'll list some that are directly used as string keys:
    # "chamberTemp", "chamberTargetTemp", "leftTemp", "leftTargetTemp", "rightTemp", "rightTargetTemp",
    # "platTemp", "platTargetTemp", "cumulativeFilament", "cumulativePrintTime", "fillAmount",
    # "leftFilamentType", "rightFilamentType", "estimatedLeftLen", "estimatedLeftWeight",
    # "estimatedRightLen", "estimatedRightWeight", "chamberFanSpeed", "coolingFanSpeed", "tvoc",
    # "remainingDiskSpace", "zAxisCompensation", "autoShutdownTime", "currentPrintSpeed",
    # "flashRegisterCode", "location", "macAddr", "measure", "nozzleCnt", "nozzleModel",
    # "nozzleStyle", "pid", "polarRegisterCode", "printSpeedAdjust"
    # And top-level custom keys used in coordinator.data
    # "printable_files", "x_position", "y_position", "z_position"
    # Note: x_position, y_position, z_position are now covered by API_ATTR_*
)
from .coordinator import FlashforgeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Centralized sensor definitions: key: (name, unit, device_class, state_class, is_top_level, is_percentage)
# Using API_ATTR_* constants as keys where applicable.
SENSOR_DEFINITIONS = {
    # Top-Level
    API_KEY_CODE: ("Status Code", None, None, SensorStateClass.MEASUREMENT, True, False), # "code"
    API_KEY_MESSAGE: ("Status Message", None, None, None, True, False), # "message"
    # Detail section - using string literals for keys that are directly from API detail object
    # and don't have a more specific API_ATTR_* constant yet (e.g. chamberTemp)
    # or if the API_ATTR_* constant matches the string literal.
    API_ATTR_STATUS: ("Status", None, None, None, False, False),
    API_ATTR_FIRMWARE_VERSION: ("Firmware Version", None, None, None, False, False),
    "chamberTemp": ( # TODO: Consider API_ATTR_CHAMBER_TEMP if defined
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
    # Example for printProgress which has API_ATTR_PRINT_PROGRESS
    API_ATTR_PRINT_PROGRESS: (
        "Print Progress",
        PERCENTAGE,
        SensorDeviceClass.BATTERY, # Using BATTERY device class for percentage
        SensorStateClass.MEASUREMENT,
        False,
        True,
    ),
    API_ATTR_PRINT_DURATION: (
        "Print Duration",
        UnitOfTime.SECONDS,
        SensorDeviceClass.DURATION, # Standard DURATION device class
        SensorStateClass.MEASUREMENT,
        False,
        False,
    ),
    API_ATTR_ESTIMATED_TIME: (
        "Estimated Time Remaining",
        UnitOfTime.SECONDS,
        SensorDeviceClass.DURATION, # Standard DURATION device class
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
    # Coordinator-populated custom keys (not directly from API attributes with these exact names)
    # These keys are used in coordinator.py: current_data["printable_files"] = ...
    # It's better to define constants for these as well if they are to be used as SENSOR_DEFINITION keys.
    # For now, leaving them as strings, but this is an area for future improvement if these keys are shared.
    "printable_files": ("Printable Files Count", "files", None, SensorStateClass.MEASUREMENT, True, False),
    API_ATTR_X_POSITION: ("X Position", UnitOfLength.MILLIMETERS, SensorDeviceClass.DISTANCE, SensorStateClass.MEASUREMENT, True, False),
    API_ATTR_Y_POSITION: ("Y Position", UnitOfLength.MILLIMETERS, SensorDeviceClass.DISTANCE, SensorStateClass.MEASUREMENT, True, False),
    API_ATTR_Z_POSITION: ("Z Position", UnitOfLength.MILLIMETERS, SensorDeviceClass.DISTANCE, SensorStateClass.MEASUREMENT, True, False),
    # Ensure all other API_ATTR_* constants used by sensors (like temperatures) are defined in const.py
    # and used here if they match the string keys. The current SENSOR_DEFINITIONS uses string literals
    # for many keys like "chamberTemp", "leftTemp", etc. These should be replaced if matching constants exist.
    # This change only replaces a few examples. A full replacement would require ensuring all corresponding
    # API_ATTR_* constants are defined in const.py and then used here.
}
# TODO: Further review SENSOR_DEFINITIONS to replace all string literal keys in this
# dictionary with their respective API_ATTR_* constants from const.py. This requires
# ensuring that all necessary API attribute string literals are defined as constants
# in const.py first. For example, "chamberTemp" should become API_ATTR_CHAMBER_TEMP
# if such a constant is defined.

# Type for SENSOR_DEFINITIONS value tuple
SensorDefinitionValue = Tuple[str, Optional[str], Optional[str], Optional[SensorStateClass], bool, bool]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Flashforge sensor entities from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: The config entry.
        async_add_entities: Callback to add entities.
    """
    coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors_to_add: List[FlashforgeSensor] = []

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


class FlashforgeSensor(FlashforgeEntity, SensorEntity): # Inherit from FlashforgeEntity
    """A sensor for one JSON field from the printer."""

    def __init__(
        self,
        coordinator: FlashforgeDataUpdateCoordinator,
        attribute_key: str,
        name: str,
        unit: Optional[str],
        device_class: Optional[SensorDeviceClass | str], # SensorDeviceClass or str
        state_class: Optional[SensorStateClass],
        is_top_level: bool,
        is_percentage: bool,
    ) -> None:
        """Initialize the Flashforge sensor.

        Args:
            coordinator: The data update coordinator.
            attribute_key: The key for this sensor's data in the coordinator_data
                           or detail dictionary within coordinator_data. Also used as
                           part of the unique ID.
            name: The suffix for the entity name (e.g., "Chamber Temperature").
            unit: The unit of measurement for the sensor.
            device_class: The device class of the sensor.
            state_class: The state class of the sensor.
            is_top_level: True if the attribute_key is at the root of coordinator.data.
            is_percentage: True if the value needs to be multiplied by 100.
        """
        # Pass name_suffix=name and unique_id_key=attribute_key to the base class.
        # attribute_key is already suitable as a unique_id_key (e.g., "chamberTemp", "printProgress").
        super().__init__(coordinator, name_suffix=name, unique_id_key=attribute_key)

        self._attribute_key: str = attribute_key
        self._is_top_level: bool = is_top_level
        self._is_percentage: bool = is_percentage

        # self._attr_name and self._attr_unique_id are set by the FlashforgeEntity base class.
        self._attr_device_class: Optional[SensorDeviceClass | str] = device_class
        self._attr_state_class: Optional[SensorStateClass] = state_class
        self._attr_native_unit_of_measurement: Optional[str] = PERCENTAGE if is_percentage else unit
        self._attr_extra_state_attributes: Dict[str, Any] = {}
        self._attr_native_value: Any = None

        # self._attr_device_info is now handled by the inherited device_info property from FlashforgeEntity.
        # The base class constructor FlashforgeEntity(coordinator) is called by super().__init__(coordinator).

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        This method is called by the SENSOR_DEFINITIONS listener when the coordinator updates.
        It fetches the new state for the sensor from `self.coordinator.data`,
        updates `self._attr_native_value` and other attributes, and calls
        `self.async_write_ha_state()` to persist the new state.
        """
        self._attr_available = self.coordinator.last_update_success
        raw_value = None
        if self.coordinator.data:
            if self._is_top_level:
                raw_value = self.coordinator.data.get(self._attribute_key)
            elif self.coordinator.data.get("detail"):
                raw_value = self.coordinator.data.get("detail", {}).get(
                    self._attribute_key
                )

        # Ensure extra_state_attributes is initialized (already done in __init__, but good for clarity)
        # self._attr_extra_state_attributes = self._attr_extra_state_attributes or {}

        # Example: If "printable_files" key was changed to a constant INTERNAL_KEY_PRINTABLE_FILES
        # if self._attribute_key == INTERNAL_KEY_PRINTABLE_FILES:
        if self._attribute_key == "printable_files": # Keeping as string for now, per above TODO
            files_list = raw_value if isinstance(raw_value, list) else []
            self._attr_native_value = len(files_list)
            self._attr_extra_state_attributes["files"] = files_list
        elif self._is_percentage and raw_value is not None:
            try:
                self._attr_native_value = round(float(raw_value) * 100.0, 1)
            except (ValueError, TypeError) as e:  # Catch specific errors
                _LOGGER.warning(
                    f"Could not convert value '{raw_value}' to percentage for sensor {self._attribute_key} ({self.name}). Error: {e}",
                    exc_info=True,
                )
                self._attr_native_value = None
        else:  # Default logic for other sensors
            self._attr_native_value = raw_value

        # Update sw_version in device_info if it changed
        if self.coordinator.data and self.coordinator.data.get(
            "detail"
        ):  # Ensure detail exists
            fw_version = self.coordinator.data.get("detail", {}).get(
                API_ATTR_FIRMWARE_VERSION
            )
            # The device_info property from FlashforgeEntity will pick up new sw_version.
            # No need to manually update self._attr_device_info['sw_version'] here if we rely on the property.
            pass # sw_version is handled by the device_info property
        self.async_write_ha_state()

    @property
    def native_value(self) -> Any: # Type hint for property getter
        """Return the state of the sensor."""
        return self._attr_native_value

    # async_added_to_hass is inherited from FlashforgeEntity
    # The inherited async_added_to_hass calls self._handle_coordinator_update.
