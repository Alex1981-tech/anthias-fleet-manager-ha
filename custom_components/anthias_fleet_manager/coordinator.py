"""DataUpdateCoordinator for Anthias Fleet Manager."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AnthiasApiError, AnthiasAuthError, AnthiasFleetManagerApi
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

MEDIA_CACHE_TTL = 300  # 5 minutes


class AnthiasCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that polls FM for player data.

    Data structure:
    {
        "player_uuid": {
            "id": "...",
            "name": "...",
            "is_online": True/False,
            "last_seen": "...",
            "info": { ... },
            "cec": { ... },
            "now_playing": { ... },
            "schedule_slots": [ ... ],
            "schedule_status": { ... },
        }
    }
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: AnthiasFleetManagerApi,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self._media_cache: list[dict] = []
        self._media_cache_ts: float = 0

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch players + info from FM."""
        try:
            players = await self.api.async_get_players()
        except AnthiasAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AnthiasApiError as err:
            raise UpdateFailed(f"Error fetching players: {err}") from err

        result: dict[str, dict[str, Any]] = {}

        for player in players:
            pid = str(player["id"])
            entry: dict[str, Any] = {
                "id": pid,
                "name": player.get("name", pid),
                "is_online": player.get("is_online", False),
                "last_seen": player.get("last_seen"),
                "info": {},
                "cec": {},
                "now_playing": None,
                "schedule_slots": [],
                "schedule_status": {},
            }

            # Use last_status from player list (already has CPU, memory, disk, uptime)
            last_status = player.get("last_status") or {}
            if last_status:
                entry["info"] = last_status

            # For online players, also fetch live info, CEC, and schedule
            if entry["is_online"]:
                try:
                    info = await self.api.async_get_player_info(pid)
                    entry["info"] = info
                except AnthiasApiError:
                    _LOGGER.debug("Could not fetch info for player %s", pid)

                try:
                    cec = await self.api.async_get_cec_status(pid)
                    entry["cec"] = cec
                except AnthiasApiError:
                    _LOGGER.debug("Could not fetch CEC status for player %s", pid)

                try:
                    now_playing = await self.api.async_get_now_playing(pid)
                    entry["now_playing"] = now_playing
                except AnthiasApiError:
                    _LOGGER.debug("Could not fetch now-playing for player %s", pid)

                try:
                    slots = await self.api.async_get_schedule_slots(pid)
                    entry["schedule_slots"] = slots
                except AnthiasApiError:
                    _LOGGER.debug("Could not fetch schedule slots for player %s", pid)

                try:
                    status = await self.api.async_get_schedule_status(pid)
                    entry["schedule_status"] = status
                except AnthiasApiError:
                    _LOGGER.debug(
                        "Could not fetch schedule status for player %s", pid
                    )

            result[pid] = entry

        return result

    async def async_get_media_files(self) -> list[dict]:
        """Get media files from FM content library (cached 5 min)."""
        now = time.monotonic()
        if now - self._media_cache_ts < MEDIA_CACHE_TTL and self._media_cache:
            return self._media_cache
        self._media_cache = await self.api.async_get_media_files()
        self._media_cache_ts = now
        return self._media_cache
