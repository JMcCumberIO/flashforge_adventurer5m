"""Button platform for Flashforge Adventurer 5M PRO integration."""
import logging
from typing import List, Callable, Optional, Dict, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SERVICE_PAUSE_PRINT,
    SERVICE_RESUME_PRINT,
    SERVICE_CANCEL_PRINT,
    SERVICE_HOME_AXES,
    SERVICE_FILAMENT_CHANGE,
    SERVICE_START_BED_LEVELING,
    API_ATTR_STATUS,
    API_ATTR_DETAIL,
    PRINTING_STATES,
    PAUSED_STATE,
    IDLE_STATES, # To determine if printer is idle for some actions
)
from .coordinator import FlashforgeDataUpdateCoordinator
from .entity import FlashforgeEntity

_LOGGER = logging.getLogger(__name__)


# --- Availability Functions ---
def _is_printing_or_paused(coordinator: FlashforgeDataUpdateCoordinator) -> bool:
    """Return True if printer is printing or paused."""
    if not coordinator.data or not isinstance(coordinator.data.get(API_ATTR_DETAIL), dict):
        return False
    status = coordinator.data[API_ATTR_DETAIL].get(API_ATTR_STATUS)
    return status in PRINTING_STATES or status == PAUSED_STATE

def _is_printing(coordinator: FlashforgeDataUpdateCoordinator) -> bool:
    """Return True if printer is actively printing (not paused)."""
    if not coordinator.data or not isinstance(coordinator.data.get(API_ATTR_DETAIL), dict):
        return False
    return coordinator.data[API_ATTR_DETAIL].get(API_ATTR_STATUS) in PRINTING_STATES

def _is_paused(coordinator: FlashforgeDataUpdateCoordinator) -> bool:
    """Return True if printer is paused."""
    if not coordinator.data or not isinstance(coordinator.data.get(API_ATTR_DETAIL), dict):
        return False
    return coordinator.data[API_ATTR_DETAIL].get(API_ATTR_STATUS) == PAUSED_STATE

def _is_idle(coordinator: FlashforgeDataUpdateCoordinator) -> bool:
    """Return True if printer is idle and not printing/paused."""
    if not coordinator.data or not isinstance(coordinator.data.get(API_ATTR_DETAIL), dict):
        return True # Default to available if status is unknown, service call will fail if not appropriate
    status = coordinator.data[API_ATTR_DETAIL].get(API_ATTR_STATUS)
    return status in IDLE_STATES or status not in PRINTING_STATES + [PAUSED_STATE]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Flashforge button entities from a config entry."""
    coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    buttons: List[ButtonEntity] = [
        PausePrintButton(coordinator),
        ResumePrintButton(coordinator),
        CancelPrintButton(coordinator),
        HomeAxesButton(coordinator),
        FilamentChangeButton(coordinator),
        StartBedLevelingButton(coordinator),
    ]
    async_add_entities(buttons)


class FlashforgeButtonEntity(FlashforgeEntity, ButtonEntity):
    """Base class for Flashforge button entities."""

    def __init__(
        self,
        coordinator: FlashforgeDataUpdateCoordinator,
        name_suffix: str,
        unique_id_key: str,
        icon: str,
        service_name: str,
        availability_func: Optional[Callable[[FlashforgeDataUpdateCoordinator], bool]] = None,
        service_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the Flashforge button entity."""
        super().__init__(coordinator, name_suffix=name_suffix, unique_id_key=unique_id_key)
        self._attr_icon = icon
        self._service_name = service_name
        self._service_data = service_data or {}
        self._availability_func = availability_func
        # Initial availability update
        if self._availability_func:
            self._attr_available = self._availability_func(self.coordinator)

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug(f"Button '{self.name}' pressed, calling service '{self._service_name}' with data: {self._service_data}")
        try:
            await self.hass.services.async_call(
                DOMAIN,
                self._service_name,
                self._service_data,
                blocking=False,
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Error calling service {self._service_name} for button {self.name}: {e}")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator to update availability."""
        new_availability = self.coordinator.last_update_success
        if self._availability_func and new_availability: # Only check specific func if coordinator is already available
            new_availability = self._availability_func(self.coordinator)

        if self._attr_available != new_availability:
            self._attr_available = new_availability
            # The super()._handle_coordinator_update() will call async_write_ha_state()
            # so we don't need to call it here if only availability changed.
            # However, FlashforgeEntity's current _handle_coordinator_update only calls async_write_ha_state.
            # To ensure it's always called if availability changes, we can call it here OR
            # rely on the fact that FlashforgeEntity's method will call it.
            # For clarity and ensuring state is written if only our specific availability changes:
            # self.async_write_ha_state() # This might lead to double write if super also writes.
            # Let's make base _handle_coordinator_update in FlashforgeEntity only set self.available
            # and let subclasses decide when to write_ha_state, or ensure super() is called last.
            # The current FlashforgeEntity._handle_coordinator_update calls async_write_ha_state().
            # So, if new_availability changes _attr_available, the subsequent call to
            # super()._handle_coordinator_update() will persist this.

        super()._handle_coordinator_update() # This calls self.async_write_ha_state() from FlashforgeEntity


# --- Specific Button Implementations ---

class PausePrintButton(FlashforgeButtonEntity):
    """Button to pause the current print."""
    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        super().__init__(
            coordinator,
            name_suffix="Pause Print",
            unique_id_key="pause_print",
            icon="mdi:pause",
            service_name=SERVICE_PAUSE_PRINT,
            availability_func=_is_printing
        )

class ResumePrintButton(FlashforgeButtonEntity):
    """Button to resume a paused print."""
    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        super().__init__(
            coordinator,
            name_suffix="Resume Print",
            unique_id_key="resume_print",
            icon="mdi:play",
            service_name=SERVICE_RESUME_PRINT,
            availability_func=_is_paused
        )

class CancelPrintButton(FlashforgeButtonEntity):
    """Button to cancel the current print."""
    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        super().__init__(
            coordinator,
            name_suffix="Cancel Print",
            unique_id_key="cancel_print",
            icon="mdi:stop",
            service_name=SERVICE_CANCEL_PRINT,
            availability_func=_is_printing_or_paused
        )

class HomeAxesButton(FlashforgeButtonEntity):
    """Button to home all printer axes."""
    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        super().__init__(
            coordinator,
            name_suffix="Home Axes",
            unique_id_key="home_axes",
            icon="mdi:home-axis-vertical", # Using a more generic home icon
            service_name=SERVICE_HOME_AXES,
            availability_func=_is_idle # Generally home when idle
            # service_data could be passed if we want specific axis homing buttons later
        )

class FilamentChangeButton(FlashforgeButtonEntity):
    """Button to initiate filament change procedure."""
    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        super().__init__(
            coordinator,
            name_suffix="Filament Change",
            unique_id_key="filament_change",
            icon="mdi:printer-3d-nozzle-alert-outline", # Icon suggesting filament action
            service_name=SERVICE_FILAMENT_CHANGE,
            availability_func=_is_idle # Typically done when idle
        )

class StartBedLevelingButton(FlashforgeButtonEntity):
    """Button to start the bed leveling procedure."""
    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        super().__init__(
            coordinator,
            name_suffix="Start Bed Leveling",
            unique_id_key="start_bed_leveling",
            icon="mdi:format-list-checks", # Icon suggesting a checklist/procedure
            service_name=SERVICE_START_BED_LEVELING,
            availability_func=_is_idle # Typically done when idle
        )

```
