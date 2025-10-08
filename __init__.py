import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_PRINTING_SCAN_INTERVAL, # Added
    DEFAULT_PRINTING_SCAN_INTERVAL # Added
)
from .coordinator import FlashforgeDataUpdateCoordinator
from homeassistant.core import ServiceCall # For type hinting

_LOGGER = logging.getLogger(__name__)

# Service Attributes
ATTR_FILE_PATH = "file_path"
ATTR_PERCENTAGE = "percentage"
ATTR_HOME_X = "x"
ATTR_HOME_Y = "y"
ATTR_HOME_Z = "z"

# Services
SERVICE_PAUSE_PRINT = "pause_print" # Added for service list
SERVICE_START_PRINT = "start_print" # Added for service list
SERVICE_CANCEL_PRINT = "cancel_print" # Added for service list
SERVICE_TOGGLE_LIGHT = "toggle_light" # Added for service list
SERVICE_RESUME_PRINT = "resume_print" # Added for service list
SERVICE_SET_EXTRUDER_TEMPERATURE = "set_extruder_temperature" # Added for service list
SERVICE_SET_BED_TEMPERATURE = "set_bed_temperature" # Added for service list
SERVICE_SET_FAN_SPEED = "set_fan_speed" # Added for service list
SERVICE_TURN_FAN_OFF = "turn_fan_off" # Added for service list
SERVICE_MOVE_AXIS = "move_axis" # Added for service list
SERVICE_DELETE_FILE = "delete_file"
SERVICE_DISABLE_STEPPERS = "disable_steppers"
SERVICE_ENABLE_STEPPERS = "enable_steppers"
SERVICE_SET_SPEED_PERCENTAGE = "set_speed_percentage"
SERVICE_SET_FLOW_PERCENTAGE = "set_flow_percentage"
SERVICE_HOME_AXES = "home_axes"
SERVICE_EMERGENCY_STOP = "emergency_stop"
# New service names
SERVICE_LIST_FILES = "list_files"
SERVICE_REPORT_FIRMWARE_CAPABILITIES = "report_firmware_capabilities"
SERVICE_PLAY_BEEP = "play_beep"
SERVICE_START_BED_LEVELING = "start_bed_leveling"
SERVICE_SAVE_SETTINGS_TO_EEPROM = "save_settings_to_eeprom" # Renamed from save_settings
SERVICE_READ_SETTINGS_FROM_EEPROM = "read_settings_from_eeprom"
# Existing services that are being ensured or potentially modified
SERVICE_FILAMENT_CHANGE = "filament_change" # Existing
SERVICE_RESTORE_FACTORY_SETTINGS = "restore_factory_settings" # Existing
SERVICE_MOVE_RELATIVE = "move_relative"


# Platforms
PLATFORMS = ["sensor", "camera", "binary_sensor"] # Define PLATFORMS


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    Set up the Flashforge Adventurer 5M integration (supports Pro and non-Pro models).
    """
    # If you don't support YAML configuration, do nothing here.
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up the Flashforge Adventurer 5M integration from a config entry.
    
    Supports both Pro and non-Pro models with lenient validation.
    """
    host = entry.data["host"]
    serial_number = entry.data["serial_number"]
    check_code = entry.data["check_code"]

    # Retrieve scan_interval (regular) from options, then data, then default
    # CONF_SCAN_INTERVAL is a HASS built-in 'scan_interval', not from our .const directly for key name
    scan_interval = entry.options.get(
        "scan_interval", # Standard Home Assistant key for scan interval
        entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    )

    # Retrieve printing_scan_interval from options, then data, then our const default
    printing_scan_interval = entry.options.get(
        CONF_PRINTING_SCAN_INTERVAL,
        entry.data.get(CONF_PRINTING_SCAN_INTERVAL, DEFAULT_PRINTING_SCAN_INTERVAL)
    )

    coordinator = FlashforgeDataUpdateCoordinator(
        hass,
        host=host,
        serial_number=serial_number,
        check_code=check_code,
        regular_scan_interval=scan_interval, # Pass as regular_scan_interval
        printing_scan_interval=printing_scan_interval # Pass new printing_scan_interval
    )

    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup to sensor and camera platforms using the updated method
    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "camera", "binary_sensor"]
    )

    # Add options update listener if not already present (standard practice)
    if not entry.update_listeners: # Check if any listeners are already attached
        entry.add_update_listener(async_reload_entry)

    # Register services
    async def handle_pause_print(call):
        """Handle the service call to pause the print."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.pause_print()

    async def handle_start_print(call):
        """Handle the service call to start a print."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        file_path = call.data.get("file_path")  # Schema ensures it's a string
        if (
            file_path is not None
        ):  # Good practice to check if required field is actually there
            await coordinator.start_print(file_path)

    async def handle_cancel_print(call):
        """Handle the service call to cancel the print."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.cancel_print()

    async def handle_toggle_light(call):
        """Handle the service call to toggle the printer's light."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        state = call.data["state"]
        await coordinator.toggle_light(state)

    async def handle_resume_print(call):
        """Handle the service call to resume the print."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.resume_print()

    async def handle_set_extruder_temperature(call):
        """Handle the service call to set the extruder temperature."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        temperature = call.data.get("temperature")  # Schema ensures it's a positive_int
        if temperature is not None:
            await coordinator.set_extruder_temperature(temperature)

    async def handle_set_bed_temperature(call):
        """Handle the service call to set the bed temperature."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        temperature = call.data.get("temperature")  # Schema ensures it's a positive_int
        if temperature is not None:
            await coordinator.set_bed_temperature(temperature)

    async def handle_set_fan_speed(call):
        """Handle the service call to set the fan speed."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        speed = call.data.get("speed")  # Schema ensures it's an int in range
        if speed is not None:
            await coordinator.set_fan_speed(speed)

    async def handle_turn_fan_off(call):
        """Handle the service call to turn the fan off."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.turn_fan_off()

    async def handle_move_axis(call):
        """Handle the service call to move printer axes."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        x = call.data.get("x")
        y = call.data.get("y")
        z = call.data.get("z")  # Schema ensures float or None
        feedrate = call.data.get("feedrate")  # Schema ensures int or None

        # No explicit conversion needed due to vol.Coerce in schema
        await coordinator.move_axis(x=x, y=y, z=z, feedrate=feedrate)

    async def handle_delete_file(call: ServiceCall) -> None:
        """Handle the delete_file service call."""
        # Simplified: using the first available coordinator.
        # Assumes only one printer is configured.
        # A more robust solution for multiple printers would involve targeting via device_id.
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

        file_path = call.data.get(ATTR_FILE_PATH)
        if not file_path: # Should be caught by schema, but good to double check
            _LOGGER.error("Service 'delete_file' called without a file_path.")
            return

        _LOGGER.info(f"Service 'delete_file' called for file: {file_path}")
        await coordinator.delete_file(file_path)

    async def handle_disable_steppers(call: ServiceCall) -> None:
        """Handle the disable_steppers service call."""
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.info(f"Service '{SERVICE_DISABLE_STEPPERS}' called.")
        await coordinator.disable_steppers()

    async def handle_enable_steppers(call: ServiceCall) -> None:
        """Handle the enable_steppers service call."""
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.info(f"Service '{SERVICE_ENABLE_STEPPERS}' called.")
        await coordinator.enable_steppers()

    async def handle_set_speed_percentage(call: ServiceCall) -> None:
        """Handle the set_speed_percentage service call."""
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

        percentage = call.data.get(ATTR_PERCENTAGE)
        if percentage is None: # Schema ensures it's an int if present
            _LOGGER.error(f"Service '{SERVICE_SET_SPEED_PERCENTAGE}' called without percentage.")
            return

        _LOGGER.info(f"Service '{SERVICE_SET_SPEED_PERCENTAGE}' called with percentage: {percentage}%")
        await coordinator.set_speed_percentage(percentage)

    async def handle_set_flow_percentage(call: ServiceCall) -> None:
        """Handle the set_flow_percentage service call."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        percentage = call.data.get(ATTR_PERCENTAGE)
        if percentage is None:
            _LOGGER.error(f"Service '{SERVICE_SET_FLOW_PERCENTAGE}' called without percentage.")
            return
        _LOGGER.info(f"Service '{SERVICE_SET_FLOW_PERCENTAGE}' called with percentage: {percentage}%")
        await coordinator.set_flow_percentage(percentage)

    async def handle_home_axes(call: ServiceCall) -> None:
        """Handle the home_axes service call."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        axes_to_home = []
        if call.data.get(ATTR_HOME_X): axes_to_home.append("X")
        if call.data.get(ATTR_HOME_Y): axes_to_home.append("Y")
        if call.data.get(ATTR_HOME_Z): axes_to_home.append("Z")
        _LOGGER.info(f"Service '{SERVICE_HOME_AXES}' called for axes: {axes_to_home if axes_to_home else 'All'}")
        await coordinator.home_axes(axes_to_home if axes_to_home else None)

    async def handle_filament_change(call: ServiceCall) -> None:
        """Handle the filament_change service call."""
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.info(f"Service '{SERVICE_FILAMENT_CHANGE}' called.")
        await coordinator.filament_change()

    async def handle_emergency_stop(call: ServiceCall) -> None:
        """Handle the emergency_stop service call."""
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.warning(f"Service '{SERVICE_EMERGENCY_STOP}' called. Printer will halt immediately.")
        await coordinator.emergency_stop()

    async def handle_save_settings_to_eeprom(call: ServiceCall) -> None: # Renamed handler
        """Handle the save_settings_to_eeprom service call."""
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.info(f"Service '{SERVICE_SAVE_SETTINGS_TO_EEPROM}' called.")
        await coordinator.save_settings_to_eeprom()

    async def handle_restore_factory_settings(call: ServiceCall) -> None:
        """Handle the restore_factory_settings service call."""
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.warning(f"Service '{SERVICE_RESTORE_FACTORY_SETTINGS}' called. This may erase calibration and settings.")
        await coordinator.restore_factory_settings()

    # Define handlers for new services
    async def handle_list_files(call: ServiceCall) -> None:
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.info(f"Service '{SERVICE_LIST_FILES}' called.")
        await coordinator.list_files()

    async def handle_report_firmware_capabilities(call: ServiceCall) -> None:
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.info(f"Service '{SERVICE_REPORT_FIRMWARE_CAPABILITIES}' called.")
        await coordinator.report_firmware_capabilities()

    SERVICE_PLAY_BEEP_SCHEMA = vol.Schema(
        {
            vol.Required("pitch"): vol.All(vol.Coerce(int), vol.Range(min=0, max=10000)),
            vol.Required("duration"): vol.All(vol.Coerce(int), vol.Range(min=0, max=10000)),
        }
    )
    async def handle_play_beep(call: ServiceCall) -> None:
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        pitch = call.data["pitch"]
        duration = call.data["duration"]
        _LOGGER.info(f"Service '{SERVICE_PLAY_BEEP}' called with pitch: {pitch}, duration: {duration}.")
        await coordinator.play_beep(pitch, duration)

    async def handle_start_bed_leveling(call: ServiceCall) -> None:
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.info(f"Service '{SERVICE_START_BED_LEVELING}' called.")
        await coordinator.start_bed_leveling()

    async def handle_read_settings_from_eeprom(call: ServiceCall) -> None:
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.info(f"Service '{SERVICE_READ_SETTINGS_FROM_EEPROM}' called.")
        await coordinator.read_settings_from_eeprom()

    SERVICE_MOVE_RELATIVE_SCHEMA = vol.Schema(
        {
            vol.Optional("x"): vol.Coerce(float),
            vol.Optional("y"): vol.Coerce(float),
            vol.Optional("z"): vol.Coerce(float),
            vol.Optional("feedrate"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        }
    )
    async def handle_move_relative(call: ServiceCall) -> None:
        coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        x = call.data.get("x")
        y = call.data.get("y")
        z = call.data.get("z")
        feedrate = call.data.get("feedrate")
        _LOGGER.info(f"Service '{SERVICE_MOVE_RELATIVE}' called with offsets: x={x}, y={y}, z={z}, feedrate={feedrate}")
        await coordinator.move_relative(x=x, y=y, z=z, feedrate=feedrate)

    # Register all services
    hass.services.async_register(DOMAIN, SERVICE_PAUSE_PRINT, handle_pause_print)
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_PRINT,
        handle_start_print,
        schema=vol.Schema(
            {
                vol.Required(ATTR_FILE_PATH): cv.string,
            }
        ),
    )
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_PRINT, handle_cancel_print)
    hass.services.async_register(
        DOMAIN,
        SERVICE_TOGGLE_LIGHT,
        handle_toggle_light,
        schema=vol.Schema(
            {
                vol.Required("state"): cv.boolean,
            }
        ),
    )
    hass.services.async_register(DOMAIN, SERVICE_RESUME_PRINT, handle_resume_print)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_EXTRUDER_TEMPERATURE,
        handle_set_extruder_temperature,
        schema=vol.Schema({vol.Required("temperature"): cv.positive_int}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BED_TEMPERATURE,
        handle_set_bed_temperature,
        schema=vol.Schema({vol.Required("temperature"): cv.positive_int}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_SPEED,
        handle_set_fan_speed,
        schema=vol.Schema(
            {vol.Required("speed"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255))}
        ),
    )
    hass.services.async_register(DOMAIN, SERVICE_TURN_FAN_OFF, handle_turn_fan_off)
    hass.services.async_register(
        DOMAIN,
        SERVICE_MOVE_AXIS,
        handle_move_axis,
        schema=vol.Schema(
            {
                vol.Optional("x"): vol.Coerce(float),
                vol.Optional("y"): vol.Coerce(float),
                vol.Optional("z"): vol.Coerce(float),
                vol.Optional("feedrate"): vol.Coerce(int),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_FILE,
        handle_delete_file,
        schema=vol.Schema(
            {
                vol.Required(ATTR_FILE_PATH): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DISABLE_STEPPERS, handle_disable_steppers
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ENABLE_STEPPERS, handle_enable_steppers
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SPEED_PERCENTAGE,
        handle_set_speed_percentage,
        schema=vol.Schema({
            vol.Required(ATTR_PERCENTAGE): vol.All(vol.Coerce(int), vol.Range(min=10, max=500))
        })
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_FLOW_PERCENTAGE, handle_set_flow_percentage,
        schema=vol.Schema({vol.Required(ATTR_PERCENTAGE): vol.All(vol.Coerce(int), vol.Range(min=50, max=200))})
    )
    hass.services.async_register(
        DOMAIN, SERVICE_HOME_AXES, handle_home_axes,
        schema=vol.Schema({
            vol.Optional(ATTR_HOME_X, default=False): cv.boolean,
            vol.Optional(ATTR_HOME_Y, default=False): cv.boolean,
            vol.Optional(ATTR_HOME_Z, default=False): cv.boolean,
        })
    )
    # Updated/Verified existing services
    hass.services.async_register(DOMAIN, SERVICE_FILAMENT_CHANGE, handle_filament_change) # Existing
    hass.services.async_register(DOMAIN, SERVICE_EMERGENCY_STOP, handle_emergency_stop) # Existing
    hass.services.async_register(DOMAIN, SERVICE_SAVE_SETTINGS_TO_EEPROM, handle_save_settings_to_eeprom) # Renamed
    hass.services.async_register(DOMAIN, SERVICE_RESTORE_FACTORY_SETTINGS, handle_restore_factory_settings) # Existing

    # Register new services
    hass.services.async_register(DOMAIN, SERVICE_LIST_FILES, handle_list_files)
    hass.services.async_register(DOMAIN, SERVICE_REPORT_FIRMWARE_CAPABILITIES, handle_report_firmware_capabilities)
    hass.services.async_register(DOMAIN, SERVICE_PLAY_BEEP, handle_play_beep, schema=SERVICE_PLAY_BEEP_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_START_BED_LEVELING, handle_start_bed_leveling)
    hass.services.async_register(DOMAIN, SERVICE_READ_SETTINGS_FROM_EEPROM, handle_read_settings_from_eeprom)
    hass.services.async_register(DOMAIN, SERVICE_MOVE_RELATIVE, handle_move_relative, schema=SERVICE_MOVE_RELATIVE_SCHEMA)

    return True


async def async_options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Handle removal/unloading of a config entry.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:  # If this was the last entry for this domain
            _LOGGER.info(
                "Last entry for domain %s unloaded; unregistering services.", DOMAIN
            )
            # Combine all service names for unregistration
            all_service_names = [
                SERVICE_PAUSE_PRINT, SERVICE_START_PRINT, SERVICE_CANCEL_PRINT,
                SERVICE_TOGGLE_LIGHT, SERVICE_RESUME_PRINT,
                SERVICE_SET_EXTRUDER_TEMPERATURE, SERVICE_SET_BED_TEMPERATURE,
                SERVICE_SET_FAN_SPEED, SERVICE_TURN_FAN_OFF, SERVICE_MOVE_AXIS,
                SERVICE_DELETE_FILE, SERVICE_DISABLE_STEPPERS, SERVICE_ENABLE_STEPPERS,
                SERVICE_SET_SPEED_PERCENTAGE, SERVICE_SET_FLOW_PERCENTAGE,
                SERVICE_HOME_AXES, SERVICE_EMERGENCY_STOP,
                # Updated/New services
                SERVICE_FILAMENT_CHANGE,
                SERVICE_SAVE_SETTINGS_TO_EEPROM, # Renamed
                SERVICE_RESTORE_FACTORY_SETTINGS,
                SERVICE_LIST_FILES,
                SERVICE_REPORT_FIRMWARE_CAPABILITIES,
                SERVICE_PLAY_BEEP,
                SERVICE_START_BED_LEVELING,
                SERVICE_READ_SETTINGS_FROM_EEPROM,
                SERVICE_MOVE_RELATIVE,
            ]
            for service_name in all_service_names:
                if service_name:
                    _LOGGER.debug("Unregistering service: %s.%s", DOMAIN, service_name)
                    hass.services.async_remove(DOMAIN, service_name)

            hass.data.pop(DOMAIN) # Remove the domain from hass.data completely

    # Remove the options listener when unloading the entry
    # This might not be strictly necessary if the entry is being fully removed,
    # but good practice if only partially unloading or if listener persists.
    # However, standard HA reload on option change doesn't usually require explicit listener removal here.

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
