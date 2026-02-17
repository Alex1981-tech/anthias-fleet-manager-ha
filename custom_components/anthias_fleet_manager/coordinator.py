"""DataUpdateCoordinator for Anthias Fleet Manager."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AnthiasApiError, AnthiasAuthError, AnthiasFleetManagerApi
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class AnthiasCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that polls FM for player data.

    Data structure:
    {
        "player_uuid": {
            "id": "...",
            "name": "...",
            "is_online": True/False,
            "last_seen": "...",
            "info": {  # only for online players
                "cpu_temp": 48.3,
                "cpu_usage": 12,
                "memory": {"total": 7820, "used": 970, ...},
                "disk_usage": {"total_gb": 28.8, "free_gb": 20.1, ...},
                "uptime": {"days": 2, "hours": 5.3},
                "anthias_version": "v1.3.1@beff593",
                "device_model": "Raspberry Pi 4 Model B Rev 1.5",
            },
            "cec": {  # only if CEC available
                "cec_available": True,
                "tv_on": True/False,
            },
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
            }

            # Use last_status from player list (already has CPU, memory, disk, uptime)
            last_status = player.get("last_status") or {}
            if last_status:
                entry["info"] = last_status

            # For online players, also fetch live info and CEC
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

            result[pid] = entry

        return result
