"""Async API client for Anthias Fleet Manager."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class AnthiasApiError(Exception):
    """Base exception for API errors."""


class AnthiasAuthError(AnthiasApiError):
    """Authentication error."""


class AnthiasFleetManagerApi:
    """Async REST client for Fleet Manager API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        token: str,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self._token}"}

    async def _get(self, path: str) -> Any:
        """Perform a GET request."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(
                url, headers=self._headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 401:
                    raise AnthiasAuthError("Invalid or expired token")
                if resp.status == 403:
                    raise AnthiasAuthError("Permission denied")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise AnthiasApiError(f"Error communicating with FM: {err}") from err

    async def _post(self, path: str, data: dict | None = None) -> Any:
        """Perform a POST request."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.post(
                url,
                headers=self._headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise AnthiasAuthError("Invalid or expired token")
                if resp.status == 403:
                    raise AnthiasAuthError("Permission denied")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise AnthiasApiError(f"Error communicating with FM: {err}") from err

    async def _patch(self, path: str, data: dict | None = None) -> Any:
        """Perform a PATCH request."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.patch(
                url,
                headers=self._headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise AnthiasAuthError("Invalid or expired token")
                if resp.status == 403:
                    raise AnthiasAuthError("Permission denied")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise AnthiasApiError(f"Error communicating with FM: {err}") from err

    # -- Authentication --

    @staticmethod
    async def async_get_token(
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        password: str,
    ) -> str:
        """Obtain auth token from FM. Used during config flow."""
        url = f"{base_url.rstrip('/')}/api/auth/token/"
        try:
            async with session.post(
                url,
                data={"username": username, "password": password},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 400:
                    data = await resp.json()
                    msg = data.get("non_field_errors", ["Invalid credentials"])[0]
                    raise AnthiasAuthError(msg)
                resp.raise_for_status()
                data = await resp.json()
                return data["token"]
        except aiohttp.ClientError as err:
            raise AnthiasApiError(f"Cannot connect to FM: {err}") from err

    # -- Players --

    async def async_get_players(self) -> list[dict]:
        """Get all players. Handles both paginated and non-paginated responses."""
        data = await self._get("/api/players/")
        # DRF paginated response has 'results' key
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    async def async_get_player_info(self, player_id: str) -> dict:
        """Get detailed info (CPU, memory, disk, uptime) for a player."""
        return await self._get(f"/api/players/{player_id}/info/")

    async def async_get_cec_status(self, player_id: str) -> dict:
        """Get CEC availability and TV power state."""
        return await self._get(f"/api/players/{player_id}/cec-status/")

    # -- CEC commands --

    async def async_cec_wake(self, player_id: str) -> dict:
        """Wake TV via HDMI-CEC."""
        return await self._post(f"/api/players/{player_id}/cec-wake/")

    async def async_cec_standby(self, player_id: str) -> dict:
        """Send TV to standby via HDMI-CEC."""
        return await self._post(f"/api/players/{player_id}/cec-standby/")

    # -- Now playing / playback --

    async def async_get_now_playing(self, player_id: str) -> dict | None:
        """Get currently playing asset."""
        data = await self._get(f"/api/players/{player_id}/now-playing/")
        # API returns null/None when nothing is playing
        if not data:
            return None
        return data

    async def async_playback_control(self, player_id: str, command: str) -> dict:
        """Send playback command (next/previous)."""
        return await self._post(
            f"/api/players/{player_id}/playback-control/",
            data={"command": command},
        )

    def get_screenshot_url(self, player_id: str) -> str:
        """Return the screenshot URL (not async — just builds the URL)."""
        return f"{self._base_url}/api/players/{player_id}/screenshot/"

    # -- Player actions --

    async def async_reboot(self, player_id: str) -> dict:
        """Reboot player."""
        return await self._post(f"/api/players/{player_id}/reboot/")

    async def async_shutdown(self, player_id: str) -> dict:
        """Shutdown player."""
        return await self._post(f"/api/players/{player_id}/shutdown/")

    # -- Assets (proxied to player via FM) --

    async def async_get_assets(self, player_id: str) -> list[dict]:
        """Get all assets on a player."""
        data = await self._get(f"/api/players/{player_id}/assets/")
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    async def async_create_asset(self, player_id: str, data: dict) -> dict:
        """Create a URL asset on a player."""
        return await self._post(f"/api/players/{player_id}/asset-create/", data)

    async def async_upload_asset(self, player_id: str, data: dict) -> dict:
        """Upload asset to a player."""
        return await self._post(f"/api/players/{player_id}/asset-upload/", data)

    async def async_update_asset(self, player_id: str, data: dict) -> dict:
        """Update asset on a player."""
        return await self._patch(f"/api/players/{player_id}/asset-update/", data)

    async def async_delete_asset(self, player_id: str, asset_id: str) -> dict:
        """Delete asset from a player."""
        return await self._post(
            f"/api/players/{player_id}/asset-delete/", {"asset_id": asset_id}
        )

    # -- Schedule (proxied to player via FM) --

    async def async_get_schedule_slots(self, player_id: str) -> list[dict]:
        """Get schedule slots for a player."""
        data = await self._get(f"/api/players/{player_id}/schedule-slots/")
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    async def async_get_schedule_status(self, player_id: str) -> dict:
        """Get schedule status for a player."""
        return await self._get(f"/api/players/{player_id}/schedule-status/")

    async def async_create_schedule_slot(self, player_id: str, data: dict) -> dict:
        """Create a schedule slot on a player."""
        return await self._post(
            f"/api/players/{player_id}/schedule-slot-create/", data
        )

    async def async_update_schedule_slot(
        self, player_id: str, slot_id: str, data: dict
    ) -> dict:
        """Update a schedule slot on a player."""
        return await self._patch(
            f"/api/players/{player_id}/schedule-slot-update/",
            {"slot_id": slot_id, **data},
        )

    async def async_delete_schedule_slot(
        self, player_id: str, slot_id: str
    ) -> dict:
        """Delete a schedule slot from a player."""
        return await self._post(
            f"/api/players/{player_id}/schedule-slot-delete/", {"slot_id": slot_id}
        )

    async def async_add_slot_item(
        self, player_id: str, slot_id: str, asset_id: str
    ) -> dict:
        """Add an asset to a schedule slot."""
        return await self._post(
            f"/api/players/{player_id}/schedule-slot-item-add/",
            {"slot_id": slot_id, "asset_id": asset_id},
        )

    async def async_remove_slot_item(
        self, player_id: str, slot_id: str, item_id: str
    ) -> dict:
        """Remove an item from a schedule slot."""
        return await self._post(
            f"/api/players/{player_id}/schedule-slot-item-remove/",
            {"slot_id": slot_id, "item_id": item_id},
        )

    # -- Content library + Deploy --

    async def async_get_media_files(self) -> list[dict]:
        """Get media files from FM content library."""
        data = await self._get("/api/media/")
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    async def async_deploy_content(self, data: dict) -> dict:
        """Deploy content from FM library to a player."""
        return await self._post("/api/deploy/", data)

    # -- Player update --

    async def async_update_check(self, player_id: str) -> dict:
        """Check if player has updates available."""
        return await self._get(f"/api/players/{player_id}/update-check/")

    async def async_trigger_update(self, player_id: str) -> dict:
        """Trigger software update on a player."""
        return await self._post(f"/api/players/{player_id}/update/")
