"""Number platform for Flashforge Adventurer 5M PRO integration."""
import logging
from typing import List, Optional

from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature, PERCENTAGE # PERCENTAGE might not be used for fan

from .const import (
    DOMAIN,
    # Service names
    SERVICE_SET_EXTRUDER_TEMPERATURE,
    SERVICE_SET_BED_TEMPERATURE,
    SERVICE_SET_FAN_SPEED,
    # Attribute keys for service calls
    ATTR_TEMPERATURE,
    ATTR_SPEED,
    # API attribute keys for current values (targets for these number entities)
    API_ATTR_DETAIL, # Parent key for detail object
    API_ATTR_LEFT_TARGET_TEMP, # Assuming left extruder is primary
    API_ATTR_PLAT_TARGET_TEMP,
    # API_ATTR_COOLING_FAN_SPEED, # This is RPM, not 0-255 setpoint
    # Min/Max constants
    MIN_EXTRUDER_TEMP, MAX_EXTRUDER_TEMP,
    MIN_BED_TEMP, MAX_BED_TEMP,
    MIN_FAN_SPEED, MAX_FAN_SPEED,
)
from .coordinator import FlashforgeDataUpdateCoordinator
from .entity import FlashforgeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Flashforge number entities from a config entry."""
    coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: List[NumberEntity] = [
        FlashforgeExtruderTemperatureNumber(coordinator),
        FlashforgeBedTemperatureNumber(coordinator),
        FlashforgeFanSpeedNumber(coordinator),
    ]
    async_add_entities(entities)


class FlashforgeExtruderTemperatureNumber(FlashforgeEntity, NumberEntity):
    """Representation of a Number entity for extruder target temperature."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_EXTRUDER_TEMP
    _attr_native_max_value = MAX_EXTRUDER_TEMP
    _attr_native_step = 1.0
    _attr_icon = "mdi:thermometer-lines" # Or mdi:printer-3d-nozzle-outline

    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, name_suffix="Extruder Target Temperature", unique_id_key="extruder_target_temp")
        self._update_internal_state() # Initial update

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_internal_state()
        super()._handle_coordinator_update()

    def _update_internal_state(self) -> None:
        """Update the internal state of the entity from coordinator data."""
        if self.coordinator.data and API_ATTR_DETAIL in self.coordinator.data:
            detail = self.coordinator.data[API_ATTR_DETAIL]
            if isinstance(detail, dict):
                 self._attr_native_value = detail.get(API_ATTR_LEFT_TARGET_TEMP)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_SET_EXTRUDER_TEMPERATURE,
            {ATTR_TEMPERATURE: int(value)},
            blocking=False,
        )
        # Optionally, optimistically update the state or wait for coordinator
        await self.coordinator.async_request_refresh()


class FlashforgeBedTemperatureNumber(FlashforgeEntity, NumberEntity):
    """Representation of a Number entity for bed target temperature."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_BED_TEMP
    _attr_native_max_value = MAX_BED_TEMP
    _attr_native_step = 1.0
    _attr_icon = "mdi:thermometer-lines" # Or mdi:texture

    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, name_suffix="Bed Target Temperature", unique_id_key="bed_target_temp")
        self._update_internal_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_internal_state()
        super()._handle_coordinator_update()

    def _update_internal_state(self) -> None:
        """Update the internal state of the entity from coordinator data."""
        if self.coordinator.data and API_ATTR_DETAIL in self.coordinator.data:
            detail = self.coordinator.data[API_ATTR_DETAIL]
            if isinstance(detail, dict):
                self._attr_native_value = detail.get(API_ATTR_PLAT_TARGET_TEMP)
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = None

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_SET_BED_TEMPERATURE,
            {ATTR_TEMPERATURE: int(value)},
            blocking=False,
        )
        await self.coordinator.async_request_refresh()


class FlashforgeFanSpeedNumber(FlashforgeEntity, NumberEntity):
    """Representation of a Number entity for fan speed (0-255)."""

    _attr_native_unit_of_measurement = None # Raw 0-255 value
    _attr_native_min_value = MIN_FAN_SPEED
    _attr_native_max_value = MAX_FAN_SPEED
    _attr_native_step = 1.0 # Or 5.0 for larger steps in UI
    _attr_icon = "mdi:fan"
    # Since we cannot reliably read the current M106 setpoint from the printer's API,
    # we might have to assume state or just make it a "write-only" like control.
    # For now, we won't try to read it back from API_ATTR_COOLING_FAN_SPEED (which is RPM).
    # The state will reflect the last value set via Home Assistant.
    _attr_assumed_state = True

    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, name_suffix="Cooling Fan Speed", unique_id_key="cooling_fan_speed_setpoint")
        # Initialize to a default or None if we don't know the last set state.
        # If we want it to remember last HA-set state across restarts, it needs persistence,
        # or we just initialize to a sensible default (e.g. 0 for off).
        self._attr_native_value: Optional[float] = None # Or 0.0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        Since we don't read the fan setpoint (0-255) from the printer,
        this entity's state is based on the last value set by Home Assistant.
        No update from coordinator data is performed for _attr_native_value here.
        We still call super()._handle_coordinator_update() for availability updates.
        """
        # self._attr_native_value remains as last set by HA or initial value.
        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        int_value = int(value)
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_SET_FAN_SPEED,
            {ATTR_SPEED: int_value},
            blocking=False,
        )
        # Optimistically update the state in Home Assistant
        self._attr_native_value = float(int_value)
        self.async_write_ha_state()
        # Request a refresh, though it won't update this entity's value from coordinator
        await self.coordinator.async_request_refresh()
