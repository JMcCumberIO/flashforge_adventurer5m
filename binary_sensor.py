"""
Binary sensor platform for Flashforge Adventurer 5M PRO.

This module implements binary sensors for monitoring the printer's various
states including:
- Printer printing status
- Door open/closed status
- Light on/off status
- Connection status
- Error state
- Auto-shutdown enabled status
- Fan activity (internal and external)
- Endstop states (X, Y, Z, filament)
- Bed leveling status
"""

import logging
import re
from typing import Any, Dict, Optional, Callable, List # Added List for type hinting

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
# CoordinatorEntity is now inherited via FlashforgeEntity
from homeassistant.const import PERCENTAGE  # Import PERCENTAGE from HA const

from .entity import FlashforgeEntity # Import the base class
from .const import (
    DOMAIN,
    PRINTING_STATES,
    ERROR_STATES,
    DOOR_OPEN,
    LIGHT_ON,
    CONNECTION_STATE_CONNECTED,
    ERROR_CODE_NONE,
    # UNIT_PROGRESS_PERCENT, # Removed: use PERCENTAGE from homeassistant.const
    AUTO_SHUTDOWN_ENABLED_STATE,
    FAN_STATUS_ON_STATE,
    API_ATTR_STATUS,
    API_ATTR_ERROR_CODE,
    API_ATTR_DOOR_STATUS,
    API_ATTR_LIGHT_STATUS,
    API_ATTR_AUTO_SHUTDOWN,
    API_ATTR_EXTERNAL_FAN_STATUS,
    API_ATTR_INTERNAL_FAN_STATUS,
    API_ATTR_PRINT_FILE_NAME,
    API_ATTR_PRINT_PROGRESS,
    API_ATTR_PRINT_LAYER,
    API_ATTR_TARGET_PRINT_LAYER,
    API_ATTR_PRINT_DURATION,
    API_ATTR_ESTIMATED_TIME,
    API_ATTR_FIRMWARE_VERSION,
    # Endstop constants
    API_ATTR_X_ENDSTOP_STATUS,
    API_ATTR_Y_ENDSTOP_STATUS,
    API_ATTR_Z_ENDSTOP_STATUS,
    API_ATTR_FILAMENT_ENDSTOP_STATUS,
    NAME_X_ENDSTOP,
    NAME_Y_ENDSTOP,
    NAME_Z_ENDSTOP,
    NAME_FILAMENT_ENDSTOP,
    ICON_X_ENDSTOP,
    ICON_Y_ENDSTOP,
    ICON_Z_ENDSTOP,
    ICON_FILAMENT_ENDSTOP,
    # Bed Leveling constants
    API_ATTR_BED_LEVELING_STATUS,
    NAME_BED_LEVELING,
    ICON_BED_LEVELING,
)
from .coordinator import FlashforgeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """
    Set up binary sensors for the Flashforge Adventurer 5M PRO.

    Args:
        hass: Home Assistant instance
        entry: The config entry
        async_add_entities: Callback to register entities
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Create a list of entities to add
    entities = [
        # Printing status
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name="Printing",
            icon="mdi:printer-3d",
            device_class=BinarySensorDeviceClass.RUNNING,
            is_printing_sensor=True,
        ),
        # Door status - Is the door open?
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name="Door Open",
            icon="mdi:door-open",
            device_class=BinarySensorDeviceClass.DOOR,
            detail_attribute=API_ATTR_DOOR_STATUS,
            value_on=DOOR_OPEN,
        ),
        # Light status - Is the light on?
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name="Light On",
            icon="mdi:lightbulb",
            device_class=BinarySensorDeviceClass.LIGHT,
            detail_attribute=API_ATTR_LIGHT_STATUS,
            value_on=LIGHT_ON,
        ),
        # Connection status
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name="Connected",
            icon="mdi:connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=None,
            connection_status_sensor=True,
        ),
        # Error status
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name="Error",
            icon="mdi:alert-circle",
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=None,
            error_sensor=True,
        ),
        # Auto Shutdown Enabled
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name="Auto Shutdown Enabled",
            icon="mdi:timer-cog-outline",  # Or mdi:power-settings
            device_class=BinarySensorDeviceClass.POWER,
            entity_category=None,
            detail_attribute=API_ATTR_AUTO_SHUTDOWN,
            value_on=AUTO_SHUTDOWN_ENABLED_STATE,
        ),
        # External Fan Active
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name="External Fan Active",
            icon="mdi:fan",
            device_class=BinarySensorDeviceClass.RUNNING,
            entity_category=None,
            detail_attribute=API_ATTR_EXTERNAL_FAN_STATUS,
            value_on=FAN_STATUS_ON_STATE,
        ),
        # Internal Fan Active
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name="Internal Fan Active",
            icon="mdi:fan",
            device_class=BinarySensorDeviceClass.RUNNING,
            entity_category=None,
            detail_attribute=API_ATTR_INTERNAL_FAN_STATUS,
            value_on=FAN_STATUS_ON_STATE,
        ),
        # Endstop Sensors
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name=NAME_X_ENDSTOP,
            icon=ICON_X_ENDSTOP,
            device_class=None,
            entity_category=None,
            detail_attribute=API_ATTR_X_ENDSTOP_STATUS,
            value_on=True, # Sensor is "on" (problem/triggered) if M119 reports triggered (True)
        ),
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name=NAME_Y_ENDSTOP,
            icon=ICON_Y_ENDSTOP,
            device_class=None,
            entity_category=None,
            detail_attribute=API_ATTR_Y_ENDSTOP_STATUS,
            value_on=True,
        ),
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name=NAME_Z_ENDSTOP,
            icon=ICON_Z_ENDSTOP,
            device_class=None,
            entity_category=None,
            detail_attribute=API_ATTR_Z_ENDSTOP_STATUS,
            value_on=True,
        ),
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name=NAME_FILAMENT_ENDSTOP,
            icon=ICON_FILAMENT_ENDSTOP,
            device_class=BinarySensorDeviceClass.PROBLEM, # Or None, or MOISTURE if it's a runout sensor
            entity_category=None,
            detail_attribute=API_ATTR_FILAMENT_ENDSTOP_STATUS,
            value_on=True, # Assuming 'triggered' means problem (filament out)
        ),
        # Bed Leveling Status Sensor
        FlashforgeBinarySensor(
            coordinator=coordinator,
            name=NAME_BED_LEVELING,
            icon=ICON_BED_LEVELING,
            device_class=None,
            entity_category=None,
            detail_attribute=API_ATTR_BED_LEVELING_STATUS,
            value_on=True
        ),
    ]

    # Register all entities with Home Assistant
    async_add_entities(entities) # entities is implicitly List[FlashforgeBinarySensor]


class FlashforgeBinarySensor(FlashforgeEntity, BinarySensorEntity): # Inherit from FlashforgeEntity
    """
    Binary sensor implementation for Flashforge Adventurer 5M PRO.

    These sensors represent boolean states from the printer API.
    """

    def __init__(
        self,
        coordinator: FlashforgeDataUpdateCoordinator,
        name: str,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        entity_category: Optional[EntityCategory] = None,
        detail_attribute: Optional[str] = None,
        value_on: Any = None,
        is_printing_sensor: bool = False,
        connection_status_sensor: bool = False,
        error_sensor: bool = False,
    ) -> None:
        """Initialize a binary sensor for Flashforge.

        Args:
            coordinator: The data update coordinator.
            name: The sensor name (used as name_suffix for FlashforgeEntity).
            icon: Icon to use for the sensor.
            device_class: Binary sensor device class.
            entity_category: Entity category (config, diagnostic, or None).
            detail_attribute: Attribute in detail dictionary to monitor.
            value_on: Value that indicates the "on" state.
            is_printing_sensor: Whether this is the printing status sensor.
            connection_status_sensor: Whether this is the connection status sensor.
            error_sensor: Whether this is the error state sensor.
        """
        # Prepare unique_id_key for the base class
        unique_id_key = name.lower().replace(" ", "_")
        super().__init__(coordinator, name_suffix=name, unique_id_key=unique_id_key)

        # self._attr_name and self._attr_unique_id are set by the FlashforgeEntity base class.
        self._attr_icon: Optional[str] = icon
        self._attr_device_class: Optional[str] = device_class
        self._attr_entity_category: Optional[EntityCategory] = entity_category

        # Specific attribute settings
        self._detail_attribute: Optional[str] = detail_attribute
        self._value_on: Any = value_on
        self._is_printing_sensor: bool = is_printing_sensor
        self._connection_status_sensor: bool = connection_status_sensor
        self._error_sensor: bool = error_sensor

        # unique_id is set by the base class.

    # _handle_coordinator_update is called by the base class listener
    # We need to ensure it updates the entity state based on new coordinator data.
    # For BinarySensor, this means re-evaluating self.is_on.
    # The base FlashforgeEntity._handle_coordinator_update calls self.async_write_ha_state(),
    # which is usually sufficient if properties like `is_on` re-evaluate correctly.
    # No specific override of _handle_coordinator_update needed here if `is_on` is dynamic.

    @property
    def is_on(self) -> bool:
        """
        Return True if the binary sensor is on.

        This method handles different types of binary sensors with different logic:
        - For printing sensor: Check if status is in the printing states list
        - For connection sensor: Check coordinator connection state
        - For error sensor: Check if error code exists or status is in error states
        - For attribute-based sensors: Compare to the expected "on" value

        Returns:
            bool: True if the sensor is in the "on" state, False otherwise
        """
        # If coordinator has no data, we can't determine state
        if not self.coordinator.data:
            _LOGGER.debug(
                f"Coordinator data not available for sensor {self.name}, returning False"
            )
            return False

        detail = self.coordinator.data.get("detail", {}) # For existing sensors that use it

        # For attribute-based sensors that get data from root of coordinator.data
        # (like the new endstop sensors)
        # We need to check coordinator.data directly, not just detail.
        # The existing logic for self._detail_attribute already does coordinator.data.get("detail", {}).get(self._detail_attribute)
        # This needs to be smarter. If is_top_level was a flag in FlashforgeBinarySensor, we could use it.
        # For now, let's assume detail_attribute sensors are always in "detail" unless it's one of the special bool flags.
        # The new endstop sensors will have their detail_attribute directly in coordinator.data.

        # Printing status sensor (uses "detail" object)
        if self._is_printing_sensor:
            status = detail.get(API_ATTR_STATUS)
            return status in PRINTING_STATES if status else False

        # Connection status sensor
        if self._connection_status_sensor:
            # Use the connection_state property if available
            if hasattr(self.coordinator, "connection_state"):
                return self.coordinator.connection_state == CONNECTION_STATE_CONNECTED
            # Fallback to checking if we have data
            return self.coordinator.last_update_success

        # Error state sensor
        if self._error_sensor:
            # Check for error code
            error_code = detail.get(API_ATTR_ERROR_CODE)
            if error_code and error_code != ERROR_CODE_NONE:
                return True

            # Check if status is an error state
            status = detail.get(API_ATTR_STATUS)
            return status in ERROR_STATES if status else False

        # For attribute-based sensors
        if self._detail_attribute:
            # Check if the attribute is expected at the root of coordinator.data
            # This applies to our new endstop sensors.
            # A more robust way would be to pass a flag like `is_top_level_attribute`
            # to the constructor, or make the sensor "smarter".
            # For now, we assume endstop and bed leveling attributes are top-level in coordinator.data
            # and others are in 'detail'.
            if self._detail_attribute in [
                API_ATTR_X_ENDSTOP_STATUS,
                API_ATTR_Y_ENDSTOP_STATUS,
                API_ATTR_Z_ENDSTOP_STATUS,
                API_ATTR_FILAMENT_ENDSTOP_STATUS,
                API_ATTR_BED_LEVELING_STATUS, # Added Bed Leveling status here
            ]:
                return self.coordinator.data.get(self._detail_attribute) == self._value_on
            else: # Existing logic for attributes within "detail"
                return detail.get(self._detail_attribute) == self._value_on

        # Default
        return False

    @property
    def available(self) -> bool:
        """
        Return if entity is available.

        The connection status sensor should always be available, even when
        the coordinator has no data. Other sensors depend on coordinator data.

        Returns:
            bool: True if available, False otherwise
        """
        if self._connection_status_sensor:
            return True
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """
        Return additional state attributes.

        For error sensors, include error details when available.
        For printing sensors, include print job information.

        Returns:
            dict: Additional attributes to expose
        """
        if not self.coordinator.data:
            return None

        detail = self.coordinator.data.get("detail", {})
        attributes = {}

        # Add error details for error sensor
        if self._error_sensor and self.is_on:
            attributes["error_code"] = detail.get(API_ATTR_ERROR_CODE)

        # Add print job details for printing sensor
        if self._is_printing_sensor and self.is_on:
            # Define which attributes to include
            print_job_attrs = [
                API_ATTR_PRINT_FILE_NAME,
                API_ATTR_PRINT_PROGRESS,
                API_ATTR_PRINT_LAYER,
                API_ATTR_TARGET_PRINT_LAYER,
                API_ATTR_PRINT_DURATION,
                API_ATTR_ESTIMATED_TIME,
            ]
            for attr_key in print_job_attrs:
                if attr_key in detail:
                    # Convert printProgress to percentage
                    if (
                        attr_key == API_ATTR_PRINT_PROGRESS
                        and detail[attr_key] is not None
                    ):
                        try:
                            progress_value = float(detail[attr_key]) * 100
                            attributes["print_progress"] = (
                                f"{progress_value:.1f}{PERCENTAGE}"  # Use HA's PERCENTAGE
                            )
                        except ValueError:
                            _LOGGER.warning(
                                f"Could not convert printProgress value '{detail[attr_key]}' to float."
                            )
                    else:
                        # Convert camelCase to snake_case for attribute names
                        snake_attr = re.sub(r"(?<!^)(?=[A-Z])", "_", attr_key).lower()
                        attributes[snake_attr] = detail[attr_key]

        return attributes if attributes else None

    @property
    # device_info property is now inherited from FlashforgeEntity
    # async_added_to_hass is now inherited from FlashforgeEntity
