"""
Coordinator for the Flashforge Adventurer 5M PRO integration.
"""

from __future__ import annotations

import asyncio
import logging
import re  # For parsing M114
from datetime import timedelta
from typing import Any, Optional, List, Dict, Coroutine # Added Dict, Coroutine

import aiohttp

from homeassistant.core import HomeAssistant # For type hinting hass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_MCODE_PORT,
    ENDPOINT_DETAIL,
    TIMEOUT_API_CALL,
    TIMEOUT_COMMAND as COORDINATOR_COMMAND_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    BACKOFF_FACTOR,
    CONNECTION_STATE_UNKNOWN,
    CONNECTION_STATE_CONNECTED,
    CONNECTION_STATE_DISCONNECTED,
    REQUIRED_RESPONSE_FIELDS,
    REQUIRED_DETAIL_FIELDS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PRINTING_SCAN_INTERVAL, # Added
    PRINTING_STATES,               # Added
    API_ATTR_STATUS,               # Added
    TCP_CMD_PRINT_FILE_PREFIX_USER,
    TCP_CMD_PRINT_FILE_PREFIX_ROOT,
    API_ATTR_DETAIL,
    # Import new Endstop constants
    API_ATTR_X_ENDSTOP_STATUS,
    API_ATTR_Y_ENDSTOP_STATUS,
    API_ATTR_Z_ENDSTOP_STATUS,
    API_ATTR_FILAMENT_ENDSTOP_STATUS,
    API_ATTR_BED_LEVELING_STATUS,
    # API Keys
    API_KEY_SERIAL_NUMBER,
    API_KEY_CHECK_CODE,
    # TCP Commands and related
    TCP_RESPONSE_TERMINATOR_OK,
    TCP_CMD_GET_BED_LEVEL_STATUS,
    TCP_CMD_GET_ENDSTOPS,
    TCP_CMD_LIST_FILES_M661,
    M661_CMD_PREFIX, # Prefix to strip from M661 response
    M661_SEPARATOR,  # Separator for M661 file list
    TCP_CMD_M661_PATH_PREFIX, # Path prefix in M661 files
    M661_FILE_EXT_GCODE,
    M661_FILE_EXT_GX,
    TCP_CMD_GET_POSITION,
    TCP_CMD_PAUSE_PRINT,
    TCP_CMD_RESUME_PRINT,
    TCP_CMD_START_PRINT_TEMPLATE,
    TCP_CMD_CANCEL_PRINT,
    TCP_CMD_LIGHT_ON_TEMPLATE, # Assuming F0 is for chamber, might need adjustment
    TCP_CMD_LIGHT_OFF,
    TCP_CMD_EXTRUDER_TEMP_TEMPLATE,
    TCP_CMD_BED_TEMP_TEMPLATE,
    TCP_CMD_FAN_SPEED_TEMPLATE,
    TCP_CMD_FAN_OFF,
    TCP_CMD_MOVE_AXIS_TEMPLATE,
    TCP_CMD_RELATIVE_POSITIONING,
    TCP_CMD_ABSOLUTE_POSITIONING,
    TCP_CMD_DELETE_FILE_TEMPLATE,
    TCP_CMD_DISABLE_STEPPERS,
    TCP_CMD_ENABLE_STEPPERS,
    TCP_CMD_SPEED_PERCENTAGE_TEMPLATE,
    TCP_CMD_FLOW_PERCENTAGE_TEMPLATE,
    TCP_CMD_HOME_AXES_TEMPLATE,
    TCP_CMD_FILAMENT_CHANGE,
    TCP_CMD_EMERGENCY_STOP,
    TCP_CMD_LIST_FILES_M20,
    TCP_CMD_REPORT_FIRMWARE_CAPS,
    TCP_CMD_PLAY_BEEP_TEMPLATE,
    TCP_CMD_START_BED_LEVELING,
    TCP_CMD_SAVE_SETTINGS_EEPROM,
    TCP_CMD_READ_SETTINGS_EEPROM,
    TCP_CMD_RESTORE_FACTORY_SETTINGS,
    # Validation limits
    MIN_EXTRUDER_TEMP, MAX_EXTRUDER_TEMP,
    MIN_BED_TEMP, MAX_BED_TEMP,
    MIN_FAN_SPEED, MAX_FAN_SPEED,
    MIN_SPEED_PERCENTAGE, MAX_SPEED_PERCENTAGE,
    MIN_FLOW_PERCENTAGE, MAX_FLOW_PERCENTAGE,
    MIN_BEEP_PITCH, MAX_BEEP_PITCH,
    MIN_BEEP_DURATION, MAX_BEEP_DURATION,
)
from .flashforge_tcp import FlashforgeTCPClient

_LOGGER = logging.getLogger(__name__)


class FlashforgeDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages fetching data and printer interactions for Flashforge Adventurer 5M series.

    This coordinator handles polling the printer for status updates via HTTP and
    provides methods for sending commands to the printer via TCP M-codes.
    It dynamically adjusts polling frequency based on printer state (printing vs. idle).
    """
    def __init__(
        self,
        hass: HomeAssistant, # Typed hass
        host: str,
        serial_number: str,
        check_code: str,
        regular_scan_interval: int = DEFAULT_SCAN_INTERVAL,
        printing_scan_interval: int = DEFAULT_PRINTING_SCAN_INTERVAL,
    ) -> None:
        """Initialize the data update coordinator.

        Args:
            hass: Home Assistant instance.
            host: The IP address or hostname of the printer.
            serial_number: The serial number of the printer.
            check_code: The check code for authenticating with the printer.
            regular_scan_interval: Polling interval when the printer is idle.
            printing_scan_interval: Polling interval when the printer is printing.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=regular_scan_interval), # Use regular_scan_interval
        )
        self.host = host
        self.serial_number = serial_number
        self.check_code = check_code
        self.regular_scan_interval = regular_scan_interval # Stored
        self.printing_scan_interval = printing_scan_interval # Stored
        self.connection_state = CONNECTION_STATE_UNKNOWN
        self.data: dict[str, Any] = (
            {}
        )  # This is first populated by the base class after _async_update_data

    async def _send_tcp_command(
        self, command: str, action: str, response_terminator: str = TCP_RESPONSE_TERMINATOR_OK
    ) -> bool:
        """Helper method to send a TCP command and handle common logic."""
        tcp_client = FlashforgeTCPClient(self.host, DEFAULT_MCODE_PORT)
        _LOGGER.info(f"Attempting to {action} using TCP command: {command.strip()}")
        try:
            success, response = await tcp_client.send_command(
                command, response_terminator=response_terminator
            )
            if success:
                _LOGGER.info(
                    f"Successfully sent {action} command. Response: {response.strip() if response else 'N/A'}"
                )
                return True
            else:
                _LOGGER.error(
                    f"Failed to send {action} command. Response/Error: {response.strip() if response else 'N/A'}"
                )
                return False
        except Exception as e:
            _LOGGER.error(f"Exception during {action} TCP command: {e}", exc_info=True)
            return False

    async def _fetch_bed_leveling_status(self) -> Dict[str, Optional[bool]]:
        """Fetches and parses bed leveling status from M420 command."""
        status_data: Dict[str, Optional[bool]] = {API_ATTR_BED_LEVELING_STATUS: None}
        command = TCP_CMD_GET_BED_LEVEL_STATUS
        action = "FETCH BED LEVELING STATUS (M420 S0)"

        tcp_client = FlashforgeTCPClient(self.host, DEFAULT_MCODE_PORT)
        _LOGGER.debug(f"Attempting to {action} using TCP command: {command.strip()}")

        try:
            success, response = await tcp_client.send_command(command, response_terminator=TCP_RESPONSE_TERMINATOR_OK)
            if success and response:
                _LOGGER.debug(f"Raw response for {action}: {response}")
                response_lower = response.lower()
                if "bed leveling is on" in response_lower:
                    status_data[API_ATTR_BED_LEVELING_STATUS] = True
                elif "bed leveling is off" in response_lower:
                    status_data[API_ATTR_BED_LEVELING_STATUS] = False
                else:
                    _LOGGER.warning(f"Could not determine bed leveling status from M420 response: {response[:200]}")
                _LOGGER.debug(f"Parsed bed leveling data: {status_data}")
            elif success:
                _LOGGER.warning(f"{action} command sent, but no parseable data in response: {response}")
            else:
                _LOGGER.error(f"Failed to send {action} command. Response/Error: {response}")
        except Exception as e:
            _LOGGER.error(f"Exception during {action} TCP command: {e}", exc_info=True)

        # tcp_client.close() is handled by FlashforgeTCPClient's finally block

        return status_data

    async def _fetch_endstop_status(self) -> Dict[str, Optional[bool]]:
        """Fetches and parses endstop status from M119 command."""
        endstop_data: Dict[str, Optional[bool]] = {
            API_ATTR_X_ENDSTOP_STATUS: None,
            API_ATTR_Y_ENDSTOP_STATUS: None,
            API_ATTR_Z_ENDSTOP_STATUS: None,
            API_ATTR_FILAMENT_ENDSTOP_STATUS: None, # Initialize, will remain None if not reported
        }
        action = "FETCH ENDSTOP STATUS (M119)" # Action description
        command = TCP_CMD_GET_ENDSTOPS

        tcp_client = FlashforgeTCPClient(self.host, DEFAULT_MCODE_PORT)
        _LOGGER.debug(f"Attempting to {action} using TCP command: {command.strip()}")

        try:
            success, response = await tcp_client.send_command(command, response_terminator=TCP_RESPONSE_TERMINATOR_OK)
            if success and response:
                _LOGGER.debug(f"Raw response for {action}: {response}")
                # Marlin typically responds with one line per endstop, e.g.:
                # x_min:open
                # y_min:open
                # z_min:TRIGGERED
                # filament:open (or some other key for filament sensor)
                lines = response.lower().split('\n')
                for line in lines:
                    line = line.strip()
                    if "x_min:" in line:
                        endstop_data[API_ATTR_X_ENDSTOP_STATUS] = "triggered" in line
                    elif "y_min:" in line:
                        endstop_data[API_ATTR_Y_ENDSTOP_STATUS] = "triggered" in line
                    elif "z_min:" in line:
                        endstop_data[API_ATTR_Z_ENDSTOP_STATUS] = "triggered" in line
                    # Adjust "filament" based on actual M119 output key for filament sensor
                    elif "filament" in line:
                        endstop_data[API_ATTR_FILAMENT_ENDSTOP_STATUS] = "triggered" in line

                _LOGGER.debug(f"Parsed endstop data: {endstop_data}")

            elif success:
                _LOGGER.warning(f"{action} command sent, but no parseable data in response: {response}")
            else:
                _LOGGER.error(f"Failed to send {action} command. Response/Error: {response}")

        except Exception as e:
            _LOGGER.error(f"Exception during {action} TCP command: {e}", exc_info=True)

        # tcp_client.close() is handled by FlashforgeTCPClient's finally block

        return endstop_data

    async def _fetch_printable_files_list(self) -> List[str]:
        """
        Fetches the list of printable files using TCP M-code ~M661.
        Expected M661 response format (observed):
        CMD M661 Received.\r\nok\r\n  (optional prefix, may vary or be absent)
        DD\x00\x00\x00\x1b::\xa3\xa3\x00\x00\x00/data/user/filament_config/ASA.txt::\x00\x00\x00/data/user/filament_config/PETG.txt...
        (The "DD..." part might be specific to some firmware/printer responses, separator seems to be "::\x00\x00\x00")
        The actual file paths start with /data/
        """
        tcp_client = FlashforgeTCPClient(self.host, DEFAULT_MCODE_PORT)
        command = TCP_CMD_LIST_FILES_M661
        action = "FETCH PRINTABLE FILES (M661)" # Action description
        files_list = []

        _LOGGER.debug(f"Attempting to {action} using TCP command: {command.strip()}")

        try:
            success, response = await tcp_client.send_command(
                command, response_terminator=TCP_RESPONSE_TERMINATOR_OK
            )

            if success and response:
                _LOGGER.debug(f"Raw response for {action}: {response}")

                payload_str = response
                # Remove known prefixes like M661_CMD_PREFIX
                # The client might have already stripped some part of it if TCP_RESPONSE_TERMINATOR_OK was found early.
                if response.startswith(M661_CMD_PREFIX): # M661_CMD_PREFIX includes "ok\r\n"
                    payload_str = response[len(M661_CMD_PREFIX):]
                elif response.startswith(TCP_RESPONSE_TERMINATOR_OK): # If only "ok\r\n" was there
                    payload_str = response[len(TCP_RESPONSE_TERMINATOR_OK):]

                _LOGGER.debug(
                    f"Payload for M661 parsing after stripping initial 'ok': '{payload_str[:200]}...'"
                )

                parts = payload_str.split(M661_SEPARATOR)
                _LOGGER.debug(
                    f"Splitting M661 payload with separator '{repr(M661_SEPARATOR)}'. Number of parts: {len(parts)}. First few parts if any: {parts[:5]}"
                )

                if len(parts) <= 1 and payload_str:
                    _LOGGER.warning(
                        f"M661 parsing: Separator '{repr(M661_SEPARATOR)}' not found or produced no splits in non-empty payload: {payload_str[:100]}..."
                    )

                for part in parts:
                    path_start_index = part.find(TCP_CMD_M661_PATH_PREFIX)
                    if path_start_index != -1:
                        file_path = part[path_start_index:]
                        _LOGGER.debug(
                            f"M661 parsing - Extracted file_path candidate: '{file_path}'"
                        )
                        if file_path:
                            cleaned_path = "".join(
                                filter(lambda x: x.isprintable(), file_path)
                            ).strip()
                            _LOGGER.debug(
                                f"M661 parsing - Cleaned path: '{cleaned_path}', Starts with {TCP_CMD_M661_PATH_PREFIX} and ends with {M661_FILE_EXT_GCODE}/{M661_FILE_EXT_GX}: {cleaned_path.startswith(TCP_CMD_M661_PATH_PREFIX) and cleaned_path.endswith((M661_FILE_EXT_GCODE, M661_FILE_EXT_GX))}"
                            )
                            if cleaned_path.startswith(
                                TCP_CMD_M661_PATH_PREFIX
                            ) and cleaned_path.endswith((M661_FILE_EXT_GCODE, M661_FILE_EXT_GX)):
                                files_list.append(cleaned_path)
                    else:
                        if (
                            part.strip()
                        ):  # Log only if part contains something other than whitespace
                            _LOGGER.debug(
                                f"M661 parsing: '{TCP_CMD_M661_PATH_PREFIX}' not found in part: '{part[:100]}...'"
                            )

                if files_list:
                    _LOGGER.info(f"Successfully parsed file list: {files_list}")
                else:
                    _LOGGER.warning(
                        f"File list parsing resulted in empty list from M661. This may be due to an unexpected response format, no files on printer, or parsing issues. Raw payload sample after prefix: {payload_str[:200]}..."
                    )

            elif (
                success
            ):  # Command sent, but response might be empty or not what we expected
                _LOGGER.warning(
                    f"{action} command sent, but no valid file list data in response: '{response[:200]}...'"
                )
            else:
                _LOGGER.error(
                    f"Failed to send {action} command. Response/Error: {response}"
                )

            return files_list
        except Exception as e:
            _LOGGER.error(f"Exception during {action} TCP command: {e}", exc_info=True)
            return []

    async def _fetch_coordinates(self) -> Optional[Dict[str, float]]:
        """Fetches and parses the printer's X,Y,Z coordinates using M-code ~M114."""
        tcp_client = FlashforgeTCPClient(self.host, DEFAULT_MCODE_PORT)
        command = TCP_CMD_GET_POSITION
        action = "FETCH COORDINATES (M114)" # Action description
        coordinates: Dict[str, float] = {}

        _LOGGER.debug(f"Attempting to {action} using TCP command: {command.strip()}")

        try:
            success, response = await tcp_client.send_command(
                command, response_terminator=TCP_RESPONSE_TERMINATOR_OK
            )
            if success and response:
                _LOGGER.debug(f"Raw response for {action}: {response}")

                match_x = re.search(r"X:([+-]?\d+\.?\d*)", response)
                match_y = re.search(r"Y:([+-]?\d+\.?\d*)", response)
                match_z = re.search(r"Z:([+-]?\d+\.?\d*)", response)

                if match_x:
                    coordinates["x"] = float(match_x.group(1))
                if match_y:
                    coordinates["y"] = float(match_y.group(1))
                if match_z:
                    coordinates["z"] = float(match_z.group(1))

                if "x" in coordinates and "y" in coordinates and "z" in coordinates:
                    _LOGGER.debug(f"Successfully parsed coordinates: {coordinates}")
                    return coordinates
                else:
                    _LOGGER.warning(
                        f"Could not parse all X,Y,Z coordinates from M114 response: {response}. Parsed: {coordinates}"
                    )
                    return None
            else:
                _LOGGER.error(
                    f"Failed to send {action} command. Response/Error: {response}"
                )
                return None
        except Exception as e:
            _LOGGER.error(f"Exception during {action} TCP command: {e}", exc_info=True)
            return None
        return None  # Should not be reached, but linters might prefer it.

    async def _async_update_data(self) -> Dict[str, Any]:
        # Determine current polling interval based on self.data from PREVIOUS poll
        # (or initial regular_scan_interval if self.data is not yet populated)
        # This logic is slightly tricky because self.update_interval is used by the *caller*
        # to schedule the *next* call to this _async_update_data.
        # So, when _async_update_data is entered, self.update_interval reflects what was decided
        # at the end of the *previous* execution of _async_update_data.

        # Fetch new data
        fresh_data = await self._fetch_data()

        # Now, based on fresh_data, decide what the *next* interval should be.
        if fresh_data:
            printer_status_detail = fresh_data.get(API_ATTR_DETAIL, {})
            current_printer_status = printer_status_detail.get(API_ATTR_STATUS) if isinstance(printer_status_detail, dict) else None

            is_printing = current_printer_status in PRINTING_STATES

            desired_interval_seconds = self.printing_scan_interval if is_printing else self.regular_scan_interval

            if self.update_interval.total_seconds() != desired_interval_seconds:
                self.update_interval = timedelta(seconds=desired_interval_seconds)
                _LOGGER.info(f"FlashForge coordinator update interval changed to {desired_interval_seconds} seconds (Status: {current_printer_status})")
            else:
                _LOGGER.debug(f"FlashForge coordinator update interval remains {desired_interval_seconds} seconds (Status: {current_printer_status})")
        else:
            _LOGGER.warning("No fresh data from _fetch_data. Interval not changed.")
            # If fetch fails, and we were on printing interval, consider reverting to regular.
            if self.update_interval.total_seconds() == self.printing_scan_interval:
                self.update_interval = timedelta(seconds=self.regular_scan_interval)
                _LOGGER.info(f"Reverting to regular scan interval ({self.regular_scan_interval}s) due to data fetch failure.")

        return fresh_data

    async def _fetch_data(self):
        """Fetch data from HTTP /detail endpoint and, on subsequent updates, files/coords via TCP."""
        current_data = {}  # Data for this specific fetch run

        # Step 1: Fetch main status data via HTTP
        url = f"http://{self.host}:{DEFAULT_PORT}{ENDPOINT_DETAIL}"
        payload = {API_KEY_SERIAL_NUMBER: self.serial_number, API_KEY_CHECK_CODE: self.check_code}
        retries = 0
        delay = RETRY_DELAY
        http_fetch_successful = False

        while retries < MAX_RETRIES:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, json=payload, timeout=TIMEOUT_API_CALL
                    ) as resp:
                        resp.raise_for_status()
                        api_response_data = await resp.json(content_type=None)
                        if self._validate_response(api_response_data):
                            self.connection_state = CONNECTION_STATE_CONNECTED
                            current_data = api_response_data
                            http_fetch_successful = True
                            _LOGGER.debug(
                                "HTTP /detail data fetched and validated successfully."
                            )
                            break
                        else:
                            _LOGGER.warning(
                                f"Invalid response structure from /detail: {api_response_data}"
                            )
                            self.connection_state = CONNECTION_STATE_DISCONNECTED
                            current_data = {}
                            http_fetch_successful = False
                            break
            except aiohttp.ClientConnectorError as e:
                _LOGGER.warning(
                    f"Fetch attempt {retries + 1} for /detail failed due to connection error: {e}"
                )
                retries += 1
            except aiohttp.ClientResponseError as e:
                _LOGGER.warning(
                    f"Fetch attempt {retries + 1} for /detail failed with HTTP status {e.status}: {e.message}"
                )
                retries += 1
            except asyncio.TimeoutError: # Specifically for asyncio.TimeoutError from the request timeout
                _LOGGER.warning(
                    f"Fetch attempt {retries + 1} for /detail timed out after {TIMEOUT_API_CALL} seconds."
                )
                retries += 1
            except aiohttp.ClientError as e: # Catch other ClientErrors
                _LOGGER.warning(
                    f"Fetch attempt {retries + 1} for /detail failed with generic ClientError: {e}"
                )
                retries += 1
                if retries < MAX_RETRIES:
                    await asyncio.sleep(delay)
                    delay *= BACKOFF_FACTOR
                else:
                    _LOGGER.error("Max retries exceeded for /detail fetching.")
                    self.connection_state = CONNECTION_STATE_DISCONNECTED
                    current_data = {}
                    http_fetch_successful = False
                    break

        # Initialize keys that will be populated by TCP calls or from previous data
        current_data["printable_files"] = (
            self.data.get("printable_files", []) if self.data else []
        )
        current_data["x_position"] = self.data.get("x_position") if self.data else None
        current_data["y_position"] = self.data.get("y_position") if self.data else None
        current_data["z_position"] = self.data.get("z_position") if self.data else None
        # Initialize endstop status keys
        current_data[API_ATTR_X_ENDSTOP_STATUS] = self.data.get(API_ATTR_X_ENDSTOP_STATUS)
        current_data[API_ATTR_Y_ENDSTOP_STATUS] = self.data.get(API_ATTR_Y_ENDSTOP_STATUS)
        current_data[API_ATTR_Z_ENDSTOP_STATUS] = self.data.get(API_ATTR_Z_ENDSTOP_STATUS)
        current_data[API_ATTR_FILAMENT_ENDSTOP_STATUS] = self.data.get(API_ATTR_FILAMENT_ENDSTOP_STATUS)
        # Initialize Bed Leveling status key
        current_data[API_ATTR_BED_LEVELING_STATUS] = self.data.get(API_ATTR_BED_LEVELING_STATUS)

        # Step 2: Fetch TCP data only if HTTP was successful and it's not the first run for the coordinator
        # self.data will be empty on the very first run initiated by async_refresh in __init__
        if http_fetch_successful and self.data:
            _LOGGER.debug(
                "Attempting to fetch TCP data (files, coordinates, endstops, bed leveling) on a subsequent update."
            )
            try:
                files_list = await self._fetch_printable_files_list()
                current_data["printable_files"] = files_list
            except Exception as e:
                _LOGGER.error(
                    f"Failed to fetch printable files list during update: {e}",
                    exc_info=True,
                )
                current_data["printable_files"] = self.data.get("printable_files", [])

            try:
                coords = await self._fetch_coordinates()
                if coords:
                    current_data["x_position"] = coords.get("x")
                    current_data["y_position"] = coords.get("y")
                    current_data["z_position"] = coords.get("z")
                else:
                    current_data["x_position"] = self.data.get("x_position")
                    current_data["y_position"] = self.data.get("y_position")
                    current_data["z_position"] = self.data.get("z_position")
            except Exception as e:
                _LOGGER.error(
                    f"Failed to fetch coordinates during update: {e}", exc_info=True
                )
                current_data["x_position"] = self.data.get("x_position")
                current_data["y_position"] = self.data.get("y_position")
                current_data["z_position"] = self.data.get("z_position")

            try:
                endstop_status = await self._fetch_endstop_status()
                current_data.update(endstop_status)
            except Exception as e:
                _LOGGER.error(f"Failed to fetch endstop status during update: {e}", exc_info=True)

            try:
                bed_level_status = await self._fetch_bed_leveling_status()
                current_data.update(bed_level_status)
            except Exception as e:
                _LOGGER.error(f"Failed to fetch bed leveling status during update: {e}", exc_info=True)

        elif http_fetch_successful and not self.data:
            _LOGGER.debug(
                "Initial successful HTTP data fetch. Deferring TCP data (files, coords, endstops, bed leveling) for next update."
            )
            # Keys already initialized to empty/None above

        if not http_fetch_successful:
            _LOGGER.debug(
                "HTTP data fetch failed, returning current_data which may be empty or partially filled with defaults."
            )
            # Ensure keys exist if current_data is {} due to total failure
            if not current_data:
                current_data = {
                    "printable_files": [],
                    "x_position": None,
                    "y_position": None,
                    "z_position": None,
                }

        return current_data

    def _validate_response(self, data: dict[str, Any]) -> bool:
        """Validate the structure of the HTTP /detail response."""
        if not all(field in data for field in REQUIRED_RESPONSE_FIELDS):
            _LOGGER.warning(
                f"Missing one or more required top-level fields: {REQUIRED_RESPONSE_FIELDS} in data: {data}"
            )
            return False
        # API_ATTR_DETAIL is "detail"
        detail_data = data.get(
            API_ATTR_DETAIL, {}
        )  # Use constant if "detail" key was an API_ATTR_
        if not isinstance(detail_data, dict) or not all(
            field in detail_data for field in REQUIRED_DETAIL_FIELDS
        ):
            _LOGGER.warning(
                f"Missing one or more required detail fields: {REQUIRED_DETAIL_FIELDS} in detail: {detail_data}"
            )
            return False
        return True

    async def _send_http_command(
        self,
        endpoint: str,
        extra_payload: Optional[Dict[str, Any]] = None,
        expect_json_response: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Sends a command via HTTP POST, wrapped with auth details."""
        url = f"http://{self.host}:{DEFAULT_PORT}{endpoint}"
        payload = {API_KEY_SERIAL_NUMBER: self.serial_number, API_KEY_CHECK_CODE: self.check_code}
        if extra_payload:
            payload.update(extra_payload)

        _LOGGER.debug(f"Sending HTTP command to {url} with payload: {payload}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, timeout=COORDINATOR_COMMAND_TIMEOUT
                ) as resp:
                    response_text = await resp.text()
                    _LOGGER.debug(
                        f"HTTP command to {endpoint} status: {resp.status}, response: {response_text}"
                    )
                    if resp.status == 200:
                        if expect_json_response:
                            return await resp.json(content_type=None)
                        return {
                            "status": "success_http_200",
                            "raw_response": response_text,
                        }
                    else:
                        _LOGGER.error(
                            f"HTTP command to {endpoint} failed with status {resp.status}. Response: {response_text}"
                        )
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            _LOGGER.error(
                f"Error sending HTTP command to {endpoint}: {e}", exc_info=True
            )
            return None
        # return None # This line is unreachable; already returned in except block.

    async def pause_print(self) -> bool:
        """Pauses the current print using TCP M-code."""
        return await self._send_tcp_command(TCP_CMD_PAUSE_PRINT, "PAUSE PRINT")

    async def resume_print(self) -> bool:
        """Resumes the current print using TCP M-code."""
        return await self._send_tcp_command(TCP_CMD_RESUME_PRINT, "RESUME PRINT")

    async def start_print(self, file_path: str) -> bool:
        """Starts a new print using TCP M-code."""
        # Determine the correct prefix for the file path
        if file_path.startswith(TCP_CMD_PRINT_FILE_PREFIX_USER):
            # Path already has the user prefix, use as is
            pass
        elif file_path.startswith(TCP_CMD_M661_PATH_PREFIX): # e.g. /data/user/somefile.gcode
             # Convert /data/user/ to 0:/user/ or /data/ to 0:/
            if file_path.startswith(f"{TCP_CMD_M661_PATH_PREFIX}user/"):
                file_path = f"{TCP_CMD_PRINT_FILE_PREFIX_USER}{file_path[len(TCP_CMD_M661_PATH_PREFIX)+len('user/'):]}"
            else: # /data/somefile.gcode
                file_path = f"{TCP_CMD_PRINT_FILE_PREFIX_ROOT}{file_path[len(TCP_CMD_M661_PATH_PREFIX):]}"
        elif file_path.startswith("/"): # Absolute path not starting with /data/ (less likely for user files)
             file_path = f"{TCP_CMD_PRINT_FILE_PREFIX_ROOT}{file_path.lstrip('/')}"
        else: # Relative path, assume it's in user directory
            file_path = f"{TCP_CMD_PRINT_FILE_PREFIX_USER}{file_path}"

        command = TCP_CMD_START_PRINT_TEMPLATE.format(file_path=file_path)
        action = f"START PRINT ({file_path})"
        return await self._send_tcp_command(command, action)

    async def cancel_print(self) -> bool:
        """Cancels the current print using TCP M-code."""
        return await self._send_tcp_command(TCP_CMD_CANCEL_PRINT, "CANCEL PRINT")

    async def toggle_light(self, on: bool) -> bool:
        """Toggles the printer light ON or OFF using TCP M-code commands."""
        if on:
            command = TCP_CMD_LIGHT_ON_TEMPLATE
            action_desc = "TURN LIGHT ON"
        else:
            command = TCP_CMD_LIGHT_OFF
            action_desc = "TURN LIGHT OFF"
        return await self._send_tcp_command(command, action_desc)

    async def set_extruder_temperature(self, temperature: int) -> bool:
        """Sets the extruder temperature using TCP M-code."""
        if not MIN_EXTRUDER_TEMP <= temperature <= MAX_EXTRUDER_TEMP:
            _LOGGER.error(
                f"Invalid extruder temperature: {temperature}. Must be between {MIN_EXTRUDER_TEMP} and {MAX_EXTRUDER_TEMP}."
            )
            return False
        command = TCP_CMD_EXTRUDER_TEMP_TEMPLATE.format(temperature=temperature)
        action = f"SET EXTRUDER TEMPERATURE to {temperature}°C"
        return await self._send_tcp_command(command, action)

    async def set_bed_temperature(self, temperature: int) -> bool:
        """Sets the bed temperature using TCP M-code."""
        if not MIN_BED_TEMP <= temperature <= MAX_BED_TEMP:
            _LOGGER.error(
                f"Invalid bed temperature: {temperature}. Must be between {MIN_BED_TEMP} and {MAX_BED_TEMP}."
            )
            return False
        command = TCP_CMD_BED_TEMP_TEMPLATE.format(temperature=temperature)
        action = f"SET BED TEMPERATURE to {temperature}°C"
        return await self._send_tcp_command(command, action)

    async def set_fan_speed(self, speed: int) -> bool:
        """Sets the fan speed using TCP M-code."""
        if not MIN_FAN_SPEED <= speed <= MAX_FAN_SPEED:
            _LOGGER.error(f"Invalid fan speed: {speed}. Must be between {MIN_FAN_SPEED} and {MAX_FAN_SPEED}.")
            return False
        command = TCP_CMD_FAN_SPEED_TEMPLATE.format(speed=speed)
        action = f"SET FAN SPEED to {speed}"
        return await self._send_tcp_command(command, action)

    async def turn_fan_off(self) -> bool:
        """Turns the fan off using TCP M-code."""
        return await self._send_tcp_command(TCP_CMD_FAN_OFF, "TURN FAN OFF")

    async def move_axis(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        feedrate: Optional[int] = None,
    ) -> bool: # Assuming it returns bool based on _send_tcp_command
        """Moves printer axes using TCP M-code G0 (or G1, G0 is usually rapid, G1 for controlled feed)."""
        command_parts: List[str] = [TCP_CMD_MOVE_AXIS_TEMPLATE] # e.g. "~G0"
        action_parts: List[str] = []

        if x is not None:
            command_parts.append(f"X{x}")
            action_parts.append(f"X to {x}")
        if y is not None:
            command_parts.append(f"Y{y}")
            action_parts.append(f"Y to {y}")
        if z is not None:
            command_parts.append(f"Z{z}")
            action_parts.append(f"Z to {z}")

        if not action_parts:  # No axis specified
            _LOGGER.error(
                "Move axis command called without specifying an axis (X, Y, or Z)."
            )
            return False

        if feedrate is not None:
            if feedrate > 0:
                command_parts.append(f"F{feedrate}")
                action_parts.append(f"at F{feedrate}")
            else:
                _LOGGER.warning(
                    f"Invalid feedrate for move axis: {feedrate}. Must be positive. Sending command without feedrate."
                )

        command = " ".join(command_parts) + "\r\n"
        action = f"MOVE AXIS ({', '.join(action_parts)})"

        return await self._send_tcp_command(command, action)

    async def move_relative(self, x: Optional[float]=None, y: Optional[float]=None, z: Optional[float]=None, feedrate: Optional[int]=None) -> bool:
        """Moves printer axes by a relative amount using G91 then G0, then restores G90."""
        _LOGGER.info(f"Attempting relative move with offsets: x={x}, y={y}, z={z} at feedrate={feedrate}")

        success_g91, _ = await self._send_tcp_command(TCP_CMD_RELATIVE_POSITIONING, "SET RELATIVE POSITIONING (G91)")
        if not success_g91:
            _LOGGER.error("Failed to set relative positioning (G91). Aborting relative move.")
            # Attempt to restore absolute positioning just in case, though G91 failure is problematic
            await self._send_tcp_command(TCP_CMD_ABSOLUTE_POSITIONING, "RESTORE ABSOLUTE POSITIONING (G90) after G91 fail")
            return False

        move_attempted = False
        success_move = True  # Default to true if no move is actually made

        command_parts = [TCP_CMD_MOVE_AXIS_TEMPLATE] # e.g. "~G0"
        action_parts_log = []
        if x is not None:
            command_parts.append(f"X{x}")
            action_parts_log.append(f"X:{x}")
        if y is not None:
            command_parts.append(f"Y{y}")
            action_parts_log.append(f"Y:{y}")
        if z is not None:
            command_parts.append(f"Z{z}")
            action_parts_log.append(f"Z:{z}")

        if feedrate is not None and feedrate > 0:
            command_parts.append(f"F{feedrate}")
            action_parts_log.append(f"F:{feedrate}")
        elif feedrate is not None: # feedrate is 0 or negative
             _LOGGER.warning(f"Invalid feedrate for relative move: {feedrate}. Must be positive. Ignoring feedrate.")


        if len(command_parts) > 1:  # More than just "~G0"
            move_attempted = True
            move_command = " ".join(command_parts) + "\r\n"
            relative_move_action_log = f"MOVE RELATIVE ({', '.join(action_parts_log)})"
            success_move, _ = await self._send_tcp_command(move_command, relative_move_action_log)
            if not success_move:
                _LOGGER.error(f"Relative move command ({move_command.strip()}) failed.")
        else:
            _LOGGER.warning("No axis offset provided for relative move. Skipping G0 command.")
            # No move was attempted, so success_move remains True

        success_g90, _ = await self._send_tcp_command(TCP_CMD_ABSOLUTE_POSITIONING, "RESTORE ABSOLUTE POSITIONING (G90)")
        if not success_g90:
            _LOGGER.error("Critical: Failed to restore absolute positioning (G90) after relative move sequence.")
            # Even if G90 fails, the overall success depends on G91 and the move itself.
            # However, a G90 failure is a significant issue for future commands.
            return False # G90 is critical to restore printer state for other operations

        if move_attempted:
            return success_g91 and success_move and success_g90
        else: # No move attempted, only G91 and G90 mattered
            return success_g91 and success_g90

    async def delete_file(self, file_path: str) -> bool:
        """Deletes a file from the printer's storage using M30."""
        command_file_path = file_path
        if not (file_path.startswith(TCP_CMD_PRINT_FILE_PREFIX_ROOT) or \
                file_path.startswith(TCP_CMD_PRINT_FILE_PREFIX_USER) or \
                file_path.startswith(TCP_CMD_M661_PATH_PREFIX)): # Check against /data/ as well
            command_file_path = f"{TCP_CMD_PRINT_FILE_PREFIX_USER}{file_path}"
        elif file_path.startswith(TCP_CMD_M661_PATH_PREFIX): # If it's /data/path/to/file.gcode
            command_file_path = f"{TCP_CMD_PRINT_FILE_PREFIX_ROOT}{file_path[len(TCP_CMD_M661_PATH_PREFIX):]}" # Convert to 0:/path/to/file.gcode
        # If already prefixed with 0:/user/ or 0:/, it's used as is.

        command = TCP_CMD_DELETE_FILE_TEMPLATE.format(file_path=command_file_path)
        action = f"DELETE FILE ({command_file_path})"
        return await self._send_tcp_command(command, action)

    async def disable_steppers(self) -> bool:
        """Disables all stepper motors on the printer (M18)."""
        return await self._send_tcp_command(TCP_CMD_DISABLE_STEPPERS, "DISABLE STEPPER MOTORS")

    async def enable_steppers(self) -> bool:
        """Enables all stepper motors on the printer (M17)."""
        return await self._send_tcp_command(TCP_CMD_ENABLE_STEPPERS, "ENABLE STEPPER MOTORS")

    async def set_speed_percentage(self, percentage: int) -> bool:
        """Sets the printer's speed factor override (M220 S<percentage>)."""
        if not MIN_SPEED_PERCENTAGE <= percentage <= MAX_SPEED_PERCENTAGE:
            _LOGGER.error(f"Invalid speed percentage: {percentage}. Must be between {MIN_SPEED_PERCENTAGE} and {MAX_SPEED_PERCENTAGE}.")
            return False
        command = TCP_CMD_SPEED_PERCENTAGE_TEMPLATE.format(percentage=percentage)
        action = f"SET SPEED PERCENTAGE to {percentage}%"
        return await self._send_tcp_command(command, action)

    async def set_flow_percentage(self, percentage: int) -> bool:
        """Sets the printer's flow rate percentage using M221."""
        if not MIN_FLOW_PERCENTAGE <= percentage <= MAX_FLOW_PERCENTAGE:
            _LOGGER.error(f"Invalid flow percentage: {percentage}. Must be between {MIN_FLOW_PERCENTAGE} and {MAX_FLOW_PERCENTAGE}.")
            return False
        command = TCP_CMD_FLOW_PERCENTAGE_TEMPLATE.format(percentage=percentage)
        action = f"SET FLOW PERCENTAGE to {percentage}%"
        return await self._send_tcp_command(command, action)

    async def home_axes(self, axes: Optional[List[str]] = None) -> bool:
        """Homes specified axes or all axes if None using G28."""
        command_base = TCP_CMD_HOME_AXES_TEMPLATE # "~G28"
        action_detail = "ALL AXES"
        if axes and isinstance(axes, list) and len(axes) > 0:
            valid_axes_to_home = "".join(ax.upper() for ax in axes if ax.upper() in ["X", "Y", "Z"])
            if valid_axes_to_home:
                command_base += f" {valid_axes_to_home}"
                action_detail = f"{valid_axes_to_home} AXES"

        command = command_base + "\r\n"
        action = f"HOME {action_detail}"
        return await self._send_tcp_command(command, action)

    async def filament_change(self) -> bool:
        """Initiates filament change procedure using M600."""
        return await self._send_tcp_command(TCP_CMD_FILAMENT_CHANGE, "FILAMENT CHANGE (M600)")

    async def emergency_stop(self) -> bool:
        """Sends emergency stop command M112."""
        # M112 might not send an 'ok', printer might just halt or restart.
        # Using default TCP_RESPONSE_TERMINATOR_OK might result in a timeout/false negative.
        return await self._send_tcp_command(TCP_CMD_EMERGENCY_STOP, "EMERGENCY STOP (M112)", response_terminator=TCP_RESPONSE_TERMINATOR_OK)

    async def list_files(self) -> bool:
        """Lists files on the printer's storage using M20."""
        command = TCP_CMD_LIST_FILES_M20
        action = "LIST FILES (M20)"
        _LOGGER.info(f"Attempting to {action}")
        success, response = await self._send_tcp_command(command, action)
        if success:
            _LOGGER.info(f"Successfully received file list response for M20. Full response logged at DEBUG level by TCP client. Response snippet: {response[:200]}...")
        return success

    async def report_firmware_capabilities(self) -> bool:
        """Reports firmware capabilities using M115."""
        command = TCP_CMD_REPORT_FIRMWARE_CAPS
        action = "REPORT FIRMWARE CAPABILITIES (M115)"
        _LOGGER.info(f"Attempting to {action}")
        success, response = await self._send_tcp_command(command, action)
        if success:
            _LOGGER.info(f"Successfully received firmware capabilities response for M115. Full response logged at DEBUG level by TCP client. Response snippet: {response[:200]}...")
        return success

    async def play_beep(self, pitch: int, duration: int) -> bool:
        """Plays a beep sound using M300."""
        if not (MIN_BEEP_PITCH <= pitch <= MAX_BEEP_PITCH):
            _LOGGER.warning(f"Pitch {pitch} Hz is out of typical range ({MIN_BEEP_PITCH}-{MAX_BEEP_PITCH} Hz). Proceeding anyway.")
        if not (MIN_BEEP_DURATION <= duration <= MAX_BEEP_DURATION):
            _LOGGER.warning(f"Duration {duration} ms is out of typical range ({MIN_BEEP_DURATION}-{MAX_BEEP_DURATION} ms). Proceeding anyway.")

        command = TCP_CMD_PLAY_BEEP_TEMPLATE.format(pitch=pitch, duration=duration)
        action = f"PLAY BEEP (Pitch: {pitch}, Duration: {duration})"
        return await self._send_tcp_command(command, action)

    async def start_bed_leveling(self) -> bool:
        """Starts the bed leveling process using G29."""
        return await self._send_tcp_command(TCP_CMD_START_BED_LEVELING, "START BED LEVELING (G29)")

    async def save_settings_to_eeprom(self) -> bool:
        """Saves settings to EEPROM using M500."""
        return await self._send_tcp_command(TCP_CMD_SAVE_SETTINGS_EEPROM, "SAVE SETTINGS TO EEPROM (M500)")

    async def read_settings_from_eeprom(self) -> bool:
        """Reads settings from EEPROM using M501."""
        command = TCP_CMD_READ_SETTINGS_EEPROM
        action = "READ SETTINGS FROM EEPROM (M501)"
        _LOGGER.info(f"Attempting to {action}")
        success, response = await self._send_tcp_command(command, action)
        if success:
            _LOGGER.info(f"Successfully read settings from EEPROM (M501). Full response logged at DEBUG level by TCP client. Response snippet: {response[:200]}...")
        return success

    async def restore_factory_settings(self) -> bool:
        """Restores factory settings using M502."""
        # M502 might also have non-standard response or cause a restart.
        return await self._send_tcp_command(TCP_CMD_RESTORE_FACTORY_SETTINGS, "RESTORE FACTORY SETTINGS (M502)", response_terminator=TCP_RESPONSE_TERMINATOR_OK)

    async def send_gcode_command(self, command: str) -> bool:
        """Sends a generic G-code/M-code command to the printer.

        Args:
            command: The raw G-code/M-code string to send.
                     It is expected to include any necessary prefixes (like '~')
                     and suffixes (like '\\r\\n').

        Returns:
            True if the command was sent successfully and acknowledged, False otherwise.
        """
        # It's assumed the user provides the exact command string the printer expects.
        # For Flashforge, this often means prefixed with '~' and suffixed with '\r\n'.
        # Example: "~M115\r\n"
        _LOGGER.info(f"Attempting to send generic G-code command: {command.strip()}")
        # The action description is generic here. More specific logging might occur in FlashforgeTCPClient.
        return await self._send_tcp_command(command, "SEND GENERIC GCODE")
