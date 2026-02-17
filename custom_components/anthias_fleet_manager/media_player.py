"""Media player platform for Anthias Fleet Manager."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import aiohttp

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AnthiasApiError
from .const import DOMAIN
from .coordinator import AnthiasCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up media player entities from a config entry."""
    coordinator: AnthiasCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AnthiasMediaPlayer(coordinator, player_id)
        for player_id in coordinator.data
    ]
    async_add_entities(entities)


class AnthiasMediaPlayer(CoordinatorEntity[AnthiasCoordinator], MediaPlayerEntity):
    """Media player entity for an Anthias digital signage player."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_has_entity_name = True
    _attr_icon = "mdi:monitor-dashboard"
    _attr_media_image_remotely_accessible = False
    _attr_supported_features = (
        MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: AnthiasCoordinator, player_id: str) -> None:
        super().__init__(coordinator)
        self._player_id = player_id
        player = coordinator.data[player_id]
        self._attr_unique_id = f"{player_id}_media_player"
        self._attr_name = f"{player['name']} Player"

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
    def state(self) -> MediaPlayerState | None:
        """Return the state of the player."""
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        if not player.get("is_online", False):
            return MediaPlayerState.OFF
        now_playing = player.get("now_playing")
        if now_playing:
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def media_title(self) -> str | None:
        """Return the title of the currently playing media."""
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        now_playing = player.get("now_playing")
        if now_playing:
            return now_playing.get("asset_name")
        return None

    @property
    def media_content_type(self) -> MediaType | str | None:
        """Return the content type of current playing media."""
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        now_playing = player.get("now_playing")
        if not now_playing:
            return None
        mimetype = now_playing.get("mimetype", "")
        if mimetype == "video":
            return MediaType.VIDEO
        if mimetype == "image":
            return MediaType.IMAGE
        if mimetype == "web":
            return MediaType.URL
        return mimetype

    @property
    def media_image_url(self) -> str | None:
        """Return screenshot URL (HA will proxy via async_get_media_image)."""
        player = self.coordinator.data.get(self._player_id)
        if player is None or not player.get("is_online", False):
            return None
        return self.coordinator.api.get_screenshot_url(self._player_id)

    @property
    def media_image_hash(self) -> str | None:
        """Change hash on every coordinator update to force image refresh."""
        player = self.coordinator.data.get(self._player_id)
        if player is None or not player.get("is_online", False):
            return None
        # Use last_seen + now_playing to generate a changing hash
        now_playing = player.get("now_playing") or {}
        key = f"{player.get('last_seen', '')}-{now_playing.get('asset_id', '')}-{now_playing.get('started_at', '')}"
        return hashlib.md5(key.encode()).hexdigest()[:8]

    async def async_get_media_image(self) -> tuple[bytes | None, str | None]:
        """Fetch screenshot via FM API (with Token auth)."""
        player = self.coordinator.data.get(self._player_id)
        if player is None or not player.get("is_online", False):
            return None, None
        url = self.coordinator.api.get_screenshot_url(self._player_id)
        try:
            async with self.coordinator.api._session.get(
                url,
                headers=self.coordinator.api._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    content_type = resp.headers.get("Content-Type", "image/png")
                    return data, content_type
        except Exception:
            _LOGGER.debug("Could not fetch screenshot for %s", self._player_id)
        return None, None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        attrs: dict[str, Any] = {}
        now_playing = player.get("now_playing")
        if now_playing:
            attrs["asset_id"] = now_playing.get("asset_id")
            attrs["mimetype"] = now_playing.get("mimetype")
            attrs["started_at"] = now_playing.get("started_at")
        return attrs if attrs else None

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self._player_id in self.coordinator.data
        )

    async def async_media_next_track(self) -> None:
        """Skip to next asset."""
        try:
            await self.coordinator.api.async_playback_control(
                self._player_id, "next"
            )
        except AnthiasApiError as err:
            _LOGGER.error("Failed next track for %s: %s", self._player_id, err)
            return
        await self.coordinator.async_request_refresh()

    async def async_media_previous_track(self) -> None:
        """Go to previous asset."""
        try:
            await self.coordinator.api.async_playback_control(
                self._player_id, "previous"
            )
        except AnthiasApiError as err:
            _LOGGER.error("Failed prev track for %s: %s", self._player_id, err)
            return
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Wake TV via CEC."""
        try:
            await self.coordinator.api.async_cec_wake(self._player_id)
        except AnthiasApiError as err:
            _LOGGER.error("Failed to turn on %s: %s", self._player_id, err)
            return
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Standby TV via CEC."""
        try:
            await self.coordinator.api.async_cec_standby(self._player_id)
        except AnthiasApiError as err:
            _LOGGER.error("Failed to turn off %s: %s", self._player_id, err)
            return
        await self.coordinator.async_request_refresh()
