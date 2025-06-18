"""Camera platform for Flashforge Adventurer 5M PRO integration."""
import logging
from typing import Callable, Optional, List # Added Optional, List

from homeassistant import config_entries, core
from homeassistant.components.mjpeg.camera import MjpegCamera
from homeassistant.helpers.entity_platform import AddEntitiesCallback
# CoordinatorEntity is now inherited via FlashforgeEntity
from .entity import FlashforgeEntity # Import the base class
from .const import (
    DOMAIN,
    API_ATTR_CAMERA_STREAM_URL,
    API_ATTR_IP_ADDR,
    API_ATTR_FIRMWARE_VERSION,
    API_ATTR_MODEL,
    MJPEG_DEFAULT_PORT,
    MJPEG_STREAM_PATH,
    MJPEG_DUMMY_URL,
    CAMERA_UI_NAME, # Default UI name for the camera
    CAMERA_DEFAULT_NAME_SUFFIX, # For FlashforgeEntity name_suffix
    UNIQUE_ID_PREFIX, # For unique ID construction if needed, though FlashforgeEntity handles it
)
from .coordinator import FlashforgeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Flashforge camera entities from a config entry.

    Args:
        hass: Home Assistant instance.
        config_entry: The config entry.
        async_add_entities: Callback to add entities.
    """
    coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    cameras: List[FlashforgeAdventurer5MCamera] = [
        FlashforgeAdventurer5MCamera(coordinator),
    ]

    async_add_entities(cameras, update_before_add=True)
    return True


class FlashforgeAdventurer5MCamera(FlashforgeEntity, MjpegCamera): # Inherit from FlashforgeEntity
    """
    A camera entity for the Flashforge Adventurer 5M PRO, using the MjpegCamera base class.
    This implementation assumes that the camera stream URL is available via the coordinator's data.
    """

    def __init__(self, coordinator: FlashforgeDataUpdateCoordinator) -> None:
        """Initialize the Flashforge camera entity.

        Args:
            coordinator: The data update coordinator.
        """
        # Initialize FlashforgeEntity for coordinator and common attrs
        # self._attr_name will be "Flashforge Camera"
        # self._attr_unique_id will be "flashforge_{serial_number}_camera"
        FlashforgeEntity.__init__(self, coordinator, name_suffix=CAMERA_DEFAULT_NAME_SUFFIX, unique_id_key="camera")
        # Note: self.coordinator is set by FlashforgeEntity's __init__.

        detail = (
            self.coordinator.data.get("detail", {}) if self.coordinator.data else {}
        )
        # serial_number for unique_id is handled by FlashforgeEntity

        # The name passed to MjpegCamera is the entity's display name in Home Assistant.
        # This can be different from self._attr_name if needed, here we use a specific constant.
        mjpeg_camera_name: str = CAMERA_UI_NAME

        # Determine initial stream URL
        initial_mjpeg_url: Optional[str] = None
        camera_stream_url_from_api: Optional[str] = detail.get(API_ATTR_CAMERA_STREAM_URL)
        ip_addr_from_api: Optional[str] = detail.get(API_ATTR_IP_ADDR)

        if camera_stream_url_from_api:
            initial_mjpeg_url = camera_stream_url_from_api
            _LOGGER.debug(f"Using 'cameraStreamUrl' from API: {initial_mjpeg_url}")
        elif ip_addr_from_api:
            initial_mjpeg_url = (
                f"http://{ip_addr_from_api}:{MJPEG_DEFAULT_PORT}{MJPEG_STREAM_PATH}"
            )
            _LOGGER.debug(
                f"'cameraStreamUrl' missing, using fallback URL constructed from ipAddr: {initial_mjpeg_url}"
            )
        else:
            _LOGGER.warning(
                f"Coordinator does not have '{API_ATTR_CAMERA_STREAM_URL}' or '{API_ATTR_IP_ADDR}' in detail data. Camera will be unavailable initially."
            )
            # MjpegCamera will be initialized with mjpeg_url=None

        MjpegCamera.__init__(
            self,
            name=mjpeg_camera_name, # Use the specific display name for MjpegCamera
            mjpeg_url=initial_mjpeg_url,  # This can be None
            still_image_url=None,  # No separate still image URL
        )
        # self._attr_unique_id is set by FlashforgeEntity
        self._attr_is_streaming = True # Specific to MjpegCamera / this camera type

        # device_info is inherited from FlashforgeEntity.
        # MjpegCamera's base Camera class will use the device_info property.
        # No need to set self._attr_device_info here.

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
                f"No '{API_ATTR_CAMERA_STREAM_URL}' in API, using fallback URL: {fallback_url}"
            )
            return fallback_url
        else:
            _LOGGER.debug(
                f"No '{API_ATTR_CAMERA_STREAM_URL}' or '{API_ATTR_IP_ADDR}' in API data for stream_source. Returning dummy URL."
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
                f"Camera '{self.name}' unavailable: Coordinator update failed."
            )
            return False
        if self._mjpeg_url is None or self._mjpeg_url == MJPEG_DUMMY_URL:
            _LOGGER.debug(
                f"Camera '{self.name}' unavailable: MJPEG stream URL is not set or is dummy ('{self._mjpeg_url}')."
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
                f"Updating camera _mjpeg_url from '{self._mjpeg_url}' to: '{effective_new_url}'"
            )
            self._mjpeg_url = effective_new_url
            # If using HA core > 2023.X.Y, this might trigger reconnection in MjpegCamera if URL changes.

        # Update device info attributes like firmware version
        # This is now handled by the inherited device_info property from FlashforgeEntity.
        # The self.async_write_ha_state() call will trigger a re-read of that property by HA.
        # No need to update self._attr_device_info directly.

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle when entity is added."""
        # Call FlashforgeEntity's async_added_to_hass to set up coordinator listener
        # and initial update.
        await FlashforgeEntity.async_added_to_hass(self)

        # Call MjpegCamera's async_added_to_hass for its specific setup (e.g., stream).
        await MjpegCamera.async_added_to_hass(self)
