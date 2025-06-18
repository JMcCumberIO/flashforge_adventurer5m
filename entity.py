"""Base entity class for Flashforge Adventurer 5M PRO integration."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import callback
from typing import Dict, Any, Optional # Import Dict, Any, Optional

from .const import (
    DOMAIN,
    API_ATTR_FIRMWARE_VERSION,
    API_ATTR_MODEL,
    API_ATTR_DETAIL,
    MANUFACTURER,
    DEVICE_MODEL_AD5M_PRO, # Default model name if API doesn't provide one
    DEVICE_NAME_DEFAULT, # Default device name for UI
    UNIQUE_ID_PREFIX,
)
from .coordinator import FlashforgeDataUpdateCoordinator


class FlashforgeEntity(CoordinatorEntity[FlashforgeDataUpdateCoordinator]):
    """Base class for Flashforge entities."""

    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator, name_suffix: str, unique_id_key: str) -> None:
        """Initialize the entity.

        Args:
            coordinator: The data update coordinator.
            name_suffix: Suffix for the entity name (e.g., "Status", "Printing").
            unique_id_key: Key for the unique ID (e.g., "status", "printing_status").
        """
        super().__init__(coordinator)
        self._attr_name: str = f"{MANUFACTURER} {name_suffix}"
        self._attr_unique_id: str = f"{UNIQUE_ID_PREFIX}{coordinator.serial_number}_{unique_id_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the printer."""
        detail: Dict[str, Any] = {}
        if self.coordinator.data and isinstance(self.coordinator.data.get(API_ATTR_DETAIL), dict):
            detail = self.coordinator.data[API_ATTR_DETAIL]

        firmware_version: Optional[str] = detail.get(API_ATTR_FIRMWARE_VERSION)
        model: str = detail.get(API_ATTR_MODEL, DEVICE_MODEL_AD5M_PRO)

        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.serial_number)},
            name=DEVICE_NAME_DEFAULT,
            manufacturer=MANUFACTURER,
            model=model,
            sw_version=firmware_version,
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass() # Call CoordinatorEntity's method
        # Register update listener
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        # Initial update
        self._handle_coordinator_update()


    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # This method should be implemented by subclasses if they need to react to coordinator updates
        # beyond what CoordinatorEntity itself handles (which is mainly triggering async_write_ha_state).
        # For many simple entities, this might just be self.async_write_ha_state().
        # However, specific entities like sensors might override this to process data.
        self.async_write_ha_state()

# Note: The _handle_coordinator_update in this base class now calls async_write_ha_state.
# Sensor and BinarySensor classes in HA often have their own _handle_coordinator_update
# that sets their internal state before calling async_write_ha_state.
# The current async_added_to_hass in those files was:
# self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
# This change makes the base class more active in updating.
# If specific entities (sensor, binary_sensor) need more detailed processing in _handle_coordinator_update,
# they will need to override it, call super()._handle_coordinator_update(), or manage their state and call self.async_write_ha_state() directly.
# For now, the provided _handle_coordinator_update and async_added_to_hass aims to cover the common pattern.
