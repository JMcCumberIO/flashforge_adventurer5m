"""
Config flow for Flashforge Adventurer 5M PRO integration.

This module handles the setup flow for the integration, including:
- Input validation
- Connection testing
- Authentication verification
- Configuration persistence
"""

import logging
import voluptuous as vol
import aiohttp
import json
import re
import ipaddress
import asyncio
from typing import Any, Dict, Optional

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PRINTING_SCAN_INTERVAL,
    CONF_PRINTING_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_HOST,
    TIMEOUT_CONNECTION_TEST,
    MAX_RETRIES,
    RETRY_DELAY,
    ENDPOINT_DETAIL,
    REQUIRED_RESPONSE_FIELDS,
    # API Keys for payload and response
    API_KEY_SERIAL_NUMBER,
    API_KEY_CHECK_CODE,
    API_KEY_CODE,
    API_KEY_MESSAGE,
    API_VALUE_SUCCESS_CODE,
    # Prefix for unique IDs
    UNIQUE_ID_PREFIX,
    MANUFACTURER
)

_LOGGER = logging.getLogger(__name__)

# Configuration schemas
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required("serial_number"): str,
        vol.Required("check_code"): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=300)
        ),
    }
)


# Custom exception classes
class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class ConnectionTimeout(exceptions.HomeAssistantError):
    """Error to indicate the connection timed out."""


class FlashforgeOptionsFlow(config_entries.OptionsFlow):
    """Handle Flashforge options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage options."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Vol.Schema handles range validation, direct creation if valid
            # The form will re-show with errors if voluptuous validation fails
            return self.async_create_entry(title="", data=user_input)

        # Use current values as defaults
        current_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_printing_scan_interval = self.config_entry.options.get(
            CONF_PRINTING_SCAN_INTERVAL,
            DEFAULT_PRINTING_SCAN_INTERVAL
        )

        # Build the options schema
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current_scan_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                vol.Required(
                    CONF_PRINTING_SCAN_INTERVAL, default=current_printing_scan_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=15)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={
                "min_scan_interval": "5",
                "max_scan_interval": "300",
                "min_printing_scan_interval": "1",
                "max_printing_scan_interval": "15",
            },
        )


class FlashforgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Flashforge Adventurer 5M PRO integration."""

    VERSION: int = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors: Dict[str, str] = {}

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "FlashforgeOptionsFlow":  # Add quotes for forward reference
        """Create the options flow."""
        return FlashforgeOptionsFlow(config_entry)

    def _validate_ip_address(self, host: str) -> Optional[str]:
        """
        Validate the IP address or hostname format.

        Args:
            host: The IP address or hostname to validate

        Returns:
            Error message if validation fails, None if validation passes
        """
        # Check if it's a valid IP address
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            # Not an IP address, check if it's a valid hostname
            if not re.match(r"^[a-zA-Z0-9\-\.]+$", host):
                return "invalid_host_format"
        return None

    def _validate_serial_number(self, serial_number: str) -> Optional[str]:
        """
        Validate the serial number format.

        Args:
            serial_number: The serial number to validate

        Returns:
            Error message if validation fails, None if validation passes
        """
        # Ensure serial number has at least minimum length
        if len(serial_number) < 6:
            return "invalid_serial_format"
        return None

    def _validate_check_code(self, check_code: str) -> Optional[str]:
        """
        Validate the check code format.

        Args:
            check_code: The check code to validate

        Returns:
            Error message if validation fails, None if validation passes
        """
        # Ensure check code has at least minimum length
        if len(check_code) < 4:
            return "invalid_check_code_format"
        return None

    async def _validate_input(self, user_input: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate the user input allows us to connect to the printer.

        Args:
            user_input: Dictionary of user provided configuration options

        Returns:
            Dictionary of validation errors, empty if validation passes
        """
        errors = {}

        # Validate IP address/hostname format
        host_error = self._validate_ip_address(user_input[CONF_HOST])
        if host_error:
            errors[CONF_HOST] = host_error

        # Validate serial number format
        serial_error = self._validate_serial_number(user_input["serial_number"])
        if serial_error:
            errors["serial_number"] = serial_error

        # Validate check code format
        check_code_error = self._validate_check_code(user_input["check_code"])
        if check_code_error:
            errors["check_code"] = check_code_error

        # If basic validation passes, test the connection
        if not errors:
            try:
                await self._test_printer_connection(
                    self.hass,
                    user_input[CONF_HOST],
                    user_input["serial_number"],
                    user_input["check_code"],
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ConnectionTimeout:
                errors["base"] = "connection_timeout"
            except Exception:
                _LOGGER.exception("Unexpected exception during connection test")
                errors["base"] = "unknown"

        return errors

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """
        Handle the initial step of the config flow.

        This step collects the printer's connection details and validates them.

        Args:
            user_input: Dictionary of user provided configuration options

        Returns:
            FlowResult directing the config flow
        """
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Validate the user input
            errors = await self._validate_input(user_input)

            if not errors:
                # Check if this printer is already configured
                serial_num = user_input["serial_number"]
                await self.async_set_unique_id(f"{UNIQUE_ID_PREFIX}{serial_num}")
                self._abort_if_unique_id_configured()

                # Create the config entry
                return self.async_create_entry(
                    title=f"{MANUFACTURER} {serial_num}", # Use MANUFACTURER constant
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        "serial_number": serial_num,
                        "check_code": user_input["check_code"],
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    },
                )

        # Show the configuration form
        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
            description_placeholders={
                "default_scan_interval": str(DEFAULT_SCAN_INTERVAL),
                "min_scan_interval": "5",
                "max_scan_interval": "300",
            },
        )

    async def _test_printer_connection(
        self, hass: HomeAssistant, host: str, serial_number: str, check_code: str
    ) -> None:
        """
        Verify the printer is reachable and credentials are valid.

        This method attempts to connect to the printer and validate the response,
        implementing retry logic for transient failures.

        Args:
            hass: HomeAssistant instance
            host: Printer's IP address or hostname
            serial_number: Printer's serial number
            check_code: Printer's check code

        Raises:
            CannotConnect: If the printer cannot be reached
            InvalidAuth: If authentication fails
            ConnectionTimeout: If the connection times out
            Exception: For other unexpected errors
        """
        url = f"http://{host}:{DEFAULT_PORT}{ENDPOINT_DETAIL}"
        payload = {API_KEY_SERIAL_NUMBER: serial_number, API_KEY_CHECK_CODE: check_code}

        for attempt in range(MAX_RETRIES):
            try:
                timeout_seconds = TIMEOUT_CONNECTION_TEST

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                    ) as resp:
                        if resp.status in (401, 403):
                            _LOGGER.error(
                                f"Authentication failed with status: {resp.status} for host {host}"
                            )
                            raise InvalidAuth("Authentication failed")

                        resp.raise_for_status()  # Raises ClientResponseError for 4xx/5xx
                        text_data = await resp.text()

                        try:
                            data = json.loads(text_data)
                        except json.JSONDecodeError as e:
                            _LOGGER.error(f"Invalid JSON response from {host}: {e}")
                            raise InvalidAuth(f"Invalid response format: {e}")

                        # Validate basic structure and success code
                        if not all(field in data for field in REQUIRED_RESPONSE_FIELDS):
                            _LOGGER.error(
                                f"Invalid response structure from {host}, missing required fields: {REQUIRED_RESPONSE_FIELDS}"
                            )
                            raise InvalidAuth("Invalid response structure")

                        if data.get(API_KEY_CODE) != API_VALUE_SUCCESS_CODE:
                            error_msg = data.get(
                                API_KEY_MESSAGE, "Unknown error from printer API"
                            )
                            _LOGGER.error(
                                f"Printer API at {host} returned error code {data.get(API_KEY_CODE)}: {error_msg}"
                            )
                            # Distinguish auth failure by API code if possible, otherwise generic error
                            # This part might need adjustment based on how printer API signals specific errors
                            if data.get(API_KEY_CODE) == 1: # Example: Assuming code 1 is auth error
                                raise InvalidAuth(f"Printer API authentication error: {error_msg}")
                            else:
                                raise InvalidAuth(f"Printer API error: {error_msg}") # Or a more generic error like CannotConnect

                        _LOGGER.info(f"Connection test to {host} successful")
                        return  # Success

            except (
                asyncio.TimeoutError
            ):  # This will be raised by ClientTimeout if it's a total timeout
                _LOGGER.warning(
                    f"Connection to {host} timed out (attempt {attempt + 1} of {MAX_RETRIES})"
                )
                if attempt == MAX_RETRIES - 1:
                    raise ConnectionTimeout(
                        f"Connection to {host} timed out after {MAX_RETRIES} attempts"
                    )

            except (
                aiohttp.ClientResponseError
            ) as e:  # Specific error for HTTP status issues
                _LOGGER.warning(
                    f"HTTP error connecting to {host} (attempt {attempt + 1} of {MAX_RETRIES}): {e.status} - {e.message}"
                )
                if attempt == MAX_RETRIES - 1:
                    raise CannotConnect(
                        f"HTTP error after {MAX_RETRIES} attempts: {e.status} - {e.message}"
                    )

            except (
                aiohttp.ClientConnectionError
            ) as e:  # More specific connection errors
                _LOGGER.warning(
                    f"Connection error to {host} (attempt {attempt + 1} of {MAX_RETRIES}): {str(e)}"
                )
                if attempt == MAX_RETRIES - 1:
                    raise CannotConnect(
                        f"Connection failed after {MAX_RETRIES} attempts: {e}"
                    )

            # General ClientError if not caught by more specific ones above
            except aiohttp.ClientError as e:
                _LOGGER.warning(
                    f"Generic ClientError connecting to {host} (attempt {attempt + 1} of {MAX_RETRIES}): {str(e)}"
                )
                if attempt == MAX_RETRIES - 1:
                    raise CannotConnect(
                        f"ClientError after {MAX_RETRIES} attempts: {e}"
                    )

            # If we are not on the last attempt, sleep and retry
            if attempt < MAX_RETRIES - 1:
                _LOGGER.debug(
                    f"Retrying connection to {host} in {RETRY_DELAY} seconds..."
                )
                await asyncio.sleep(RETRY_DELAY)
            # If it IS the last attempt and we haven't raised an exception yet (e.g. InvalidAuth was caught by the outer handler),
            # then the loop will terminate and an exception should have been raised from within.
            # The final raise below the loop is removed.
