"""Select platform for Flashforge Adventurer 5M PRO integration."""
import logging
from typing import List, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SERVICE_START_PRINT,
    ATTR_FILE_PATH,
    API_ATTR_STATUS,
    API_ATTR_PRINT_FILE_NAME,
    PRINTING_STATES,
    API_ATTR_DETAIL,
)
from .coordinator import FlashforgeDataUpdateCoordinator
from .entity import FlashforgeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Flashforge select entities from a config entry."""
    coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: List[SelectEntity] = [
        FlashforgePrintFileSelect(coordinator),
    ]
    async_add_entities(entities)


class FlashforgePrintFileSelect(FlashforgeEntity, SelectEntity):
    """Representation of a Select entity for choosing a file to print."""

    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, name_suffix="Print File", unique_id_key="print_file_select")
        self._attr_icon: str = "mdi:file-document-outline" # Using a more generic file icon
        self._attr_options: List[str] = []
        self._attr_current_option: Optional[str] = None
        self._update_attributes_from_coordinator() # Initial update

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attributes_from_coordinator()
        super()._handle_coordinator_update() # Calls self.async_write_ha_state()

    def _update_attributes_from_coordinator(self) -> None:
        """Update entity attributes based on coordinator data."""
        if self.coordinator.data:
            # Update options (list of printable files)
            self._attr_options = self.coordinator.data.get("printable_files", [])

            # Update current_option
            detail_data = self.coordinator.data.get(API_ATTR_DETAIL, {})
            current_status = detail_data.get(API_ATTR_STATUS)
            current_printing_file = detail_data.get(API_ATTR_PRINT_FILE_NAME)

            if current_status in PRINTING_STATES and current_printing_file:
                # The API might return a full path for printFileName, or just the name.
                # We need to ensure it matches an option in self._attr_options.
                #
                # If a TypeSafe API key is configured, the coordinator already
                # resolved this (see _resolve_current_print_file) using a
                # semantic match instead of a suffix heuristic -- prefer that
                # when present. It's None when unconfigured, when there's no
                # active print, or when the judgment itself found no match,
                # so the original heuristic below still runs as a fallback.
                resolved = self.coordinator.data.get("resolved_current_print_file")
                if resolved and resolved in self._attr_options:
                    self._attr_current_option = resolved
                elif current_printing_file in self._attr_options:
                    self._attr_current_option = current_printing_file
                else:
                    # Legacy fallback: check if any option is a suffix of
                    # current_printing_file or vice-versa for basic matching.
                    # Known to be imprecise -- e.g. it can match "Snowflake.gcode"
                    # against a candidate "Snowflakex3.gcode" that shares a
                    # prefix -- kept only as a last resort when TypeSafe isn't
                    # configured.
                    found_match = False
                    for option_path in self._attr_options:
                        if current_printing_file.endswith(option_path) or option_path.endswith(current_printing_file):
                            self._attr_current_option = option_path
                            found_match = True
                            break
                    if not found_match:
                        self._attr_current_option = None
                        # Or, could add current_printing_file to options if desired, but that might get messy.
            else:
                self._attr_current_option = None
        else:
            self._attr_options = []
            self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug(f"User selected file to print: {option}")
        try:
            await self.hass.services.async_call(
                DOMAIN,
                SERVICE_START_PRINT,
                {ATTR_FILE_PATH: option},
                blocking=False,
            )
            # Optimistically set current option, will be properly updated by coordinator
            # self._attr_current_option = option
            # self.async_write_ha_state()
            # Decided against optimistic update here, let coordinator state drive it.
        except Exception as e:
            _LOGGER.error(f"Error calling start_print service for option {option}: {e}")
            # Optionally, reset current_option or show an error if the UI supports it
            # self._attr_current_option = None
            # self.async_write_ha_state()

        # Request a refresh from the coordinator to get the latest status quickly
        # This helps reflect the "printing" state sooner if the call was successful
        await self.coordinator.async_request_refresh()
