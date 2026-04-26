import logging
from typing import Callable

from homeassistant import config_entries, core
from homeassistant.components.mjpeg.camera import MjpegCamera
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    API_ATTR_CAMERA_STREAM_URL,
    API_ATTR_IP_ADDR,
    API_ATTR_FIRMWARE_VERSION,
    API_ATTR_MODEL,
    MJPEG_DEFAULT_PORT,
    MJPEG_STREAM_PATH,
    MJPEG_DUMMY_URL,
)
from .coordinator import FlashforgeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: Callable,
) -> bool:
    """
    Set up camera entities for the Flashforge Adventurer 5M PRO via a config entry.
    """
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    cameras = [
        FlashforgeAdventurer5MCamera(coordinator),
    ]

    async_add_entities(cameras, update_before_add=True)
    return True


class FlashforgeAdventurer5MCamera(CoordinatorEntity, MjpegCamera):
    """
    A camera entity for the Flashforge Adventurer 5M PRO, using the MjpegCamera base class.
    This implementation assumes that the camera stream URL is available via the coordinator's data.
    """

    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator):
        CoordinatorEntity.__init__(self, coordinator)
        self.coordinator = coordinator

        detail = (
            self.coordinator.data.get("detail", {}) if self.coordinator.data else {}
        )
        serial_number = getattr(self.coordinator, "serial_number", "unknown")
        name = "Flashforge Adventurer 5M PRO Camera"

        # Determine initial stream URL
        initial_mjpeg_url = None
        camera_stream_url_from_api = detail.get(API_ATTR_CAMERA_STREAM_URL)
        ip_addr_from_api = detail.get(API_ATTR_IP_ADDR)

        if camera_stream_url_from_api:
            initial_mjpeg_url = camera_stream_url_from_api
            _LOGGER.debug("Using 'cameraStreamUrl' from API: %s", initial_mjpeg_url)
        elif ip_addr_from_api:
            initial_mjpeg_url = (
                f"http://{ip_addr_from_api}:{MJPEG_DEFAULT_PORT}{MJPEG_STREAM_PATH}"
            )
            _LOGGER.debug(
                "'cameraStreamUrl' missing, using fallback URL constructed from ipAddr: %s",
                initial_mjpeg_url,
            )
        else:
            _LOGGER.warning(
                "Coordinator does not have '%s' or '%s' in detail data. Camera will be unavailable initially.",
                API_ATTR_CAMERA_STREAM_URL,
                API_ATTR_IP_ADDR,
            )
            # MjpegCamera will be initialized with mjpeg_url=None

        MjpegCamera.__init__(
            self,
            name=name,
            mjpeg_url=initial_mjpeg_url or MJPEG_DUMMY_URL,
            still_image_url=None,  # No separate still image URL
        )
        self._attr_unique_id = f"flashforge_{serial_number}_camera"
        self._attr_is_streaming = True

        # CRITICAL: Assign device_info, do NOT return it
        self._attr_device_info = {
            "identifiers": {(DOMAIN, serial_number)},
            "name": "Flashforge Adventurer 5M PRO",
            "manufacturer": "Flashforge",
            "model": detail.get(
                API_ATTR_MODEL, "Adventurer 5M PRO"
            ),  # Use constant for model key
            "sw_version": detail.get(
                API_ATTR_FIRMWARE_VERSION
            ),  # Use constant for firmware key
        }

    @property
    def stream_source(self) -> str | None:
        """Return the camera stream URL for Home Assistant."""
        # This property is called by MjpegCamera base class logic.
        # It should return a valid URL if available, or None/dummy if not.
        # The _mjpeg_url attribute of the MjpegCamera class is what's actively used.
        # This property effectively tells the base class what the *current* best source is.
        detail = (
            self.coordinator.data.get("detail", {}) if self.coordinator.data else {}
        )
        camera_stream_url_from_api = detail.get(API_ATTR_CAMERA_STREAM_URL)
        ip_addr_from_api = detail.get(API_ATTR_IP_ADDR)

        if camera_stream_url_from_api:
            return camera_stream_url_from_api
        elif ip_addr_from_api:
            fallback_url = (
                f"http://{ip_addr_from_api}:{MJPEG_DEFAULT_PORT}{MJPEG_STREAM_PATH}"
            )
            _LOGGER.debug(
                "No '%s' in API, using fallback URL: %s",
                API_ATTR_CAMERA_STREAM_URL,
                fallback_url,
            )
            return fallback_url
        else:
            _LOGGER.debug(
                "No '%s' or '%s' in API data for stream_source. Returning dummy URL.",
                API_ATTR_CAMERA_STREAM_URL,
                API_ATTR_IP_ADDR,
            )
            return MJPEG_DUMMY_URL  # Indicates no valid current source

    @property
    def available(self) -> bool:
        """Return True if the camera is available."""
        # Camera is available if the coordinator has data and the MJPEG URL is valid (not None and not dummy).
        # self._mjpeg_url is the internal URL used by the MjpegCamera base class.
        # It's updated by _handle_coordinator_update.
        if not self.coordinator.last_update_success:
            _LOGGER.debug(
                "Camera '%s' unavailable: Coordinator update failed.", self.name
            )
            return False
        if self._mjpeg_url is None or self._mjpeg_url == MJPEG_DUMMY_URL:
            _LOGGER.debug(
                "Camera '%s' unavailable: MJPEG stream URL is not set or is dummy ('%s').",
                self.name,
                self._mjpeg_url,
            )
            return False
        return True

    def _handle_coordinator_update(self) -> None:
        """Update stream URL and device info if coordinator data changes."""
        # Get the current best stream source based on coordinator data
        new_url_candidate = self.stream_source

        # If the new candidate is the dummy URL, it means no valid source is currently available.
        # In this case, we might want to set _mjpeg_url to None or the dummy URL
        # to make it unavailable. MjpegCamera base class might try to reconnect if URL changes.
        # If new_url_candidate is MJPEG_DUMMY_URL, we ensure _mjpeg_url reflects that.

        effective_new_url = new_url_candidate
        if new_url_candidate == MJPEG_DUMMY_URL:
            # If current source resolves to dummy, treat it as if no URL is available for MjpegCamera.
            # This helps ensure `available` property works correctly.
            # The base MjpegCamera class might try to use mjpeg_url=None or an empty string.
            # Setting it to DUMMY_URL explicitly makes our `available` check robust.
            effective_new_url = MJPEG_DUMMY_URL

        if effective_new_url != self._mjpeg_url:
            _LOGGER.debug(
                "Updating camera _mjpeg_url from '%s' to: '%s'",
                self._mjpeg_url,
                effective_new_url,
            )
            self._mjpeg_url = effective_new_url
            # If using HA core > 2023.X.Y, this might trigger reconnection in MjpegCamera if URL changes.

        # Update device info attributes like firmware version
        if (
            self.coordinator.data and self._attr_device_info
        ):  # Ensure data and device_info exist
            detail = self.coordinator.data.get("detail", {})
            fw_version = detail.get(API_ATTR_FIRMWARE_VERSION)
            if fw_version and self._attr_device_info.get("sw_version") != fw_version:
                self._attr_device_info["sw_version"] = fw_version

        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Register for coordinator updates and update state on add."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
