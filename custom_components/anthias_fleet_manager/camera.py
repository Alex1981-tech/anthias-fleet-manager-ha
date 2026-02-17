"""Camera platform for Anthias Fleet Manager — live screenshot."""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnthiasCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up camera entities from a config entry."""
    coordinator: AnthiasCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AnthiasScreenshotCamera(coordinator, player_id)
        for player_id in coordinator.data
    ]
    async_add_entities(entities)


class AnthiasScreenshotCamera(CoordinatorEntity[AnthiasCoordinator], Camera):
    """Camera entity showing live screenshot from Anthias player."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:monitor-screenshot"

    def __init__(self, coordinator: AnthiasCoordinator, player_id: str) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._player_id = player_id
        player = coordinator.data[player_id]
        self._attr_unique_id = f"{player_id}_screenshot"
        self._attr_name = f"{player['name']} Screenshot"

    @property
    def device_info(self):
        player = self.coordinator.data.get(self._player_id, {})
        info = player.get("info", {})
        return {
            "identifiers": {(DOMAIN, self._player_id)},
            "name": player.get("name", self._player_id),
            "manufacturer": "Anthias",
            "model": info.get("device_model", "Anthias Player"),
            "sw_version": info.get("anthias_version"),
        }

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        player = self.coordinator.data.get(self._player_id)
        return player is not None and player.get("is_online", False)

    @property
    def is_on(self) -> bool:
        """Camera is on when player is online."""
        player = self.coordinator.data.get(self._player_id)
        return player is not None and player.get("is_online", False)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return screenshot image bytes from FM API."""
        player = self.coordinator.data.get(self._player_id)
        if player is None or not player.get("is_online", False):
            return None
        url = self.coordinator.api.get_screenshot_url(self._player_id)
        try:
            async with self.coordinator.api._session.get(
                url,
                headers=self.coordinator.api._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception:
            _LOGGER.debug("Could not fetch screenshot for %s", self._player_id)
        return None

    @property
    def frame_interval(self) -> float:
        """Refresh every 10 seconds."""
        return 10.0
