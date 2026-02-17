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

    # -- Player actions --

    async def async_reboot(self, player_id: str) -> dict:
        """Reboot player."""
        return await self._post(f"/api/players/{player_id}/reboot/")

    async def async_shutdown(self, player_id: str) -> dict:
        """Shutdown player."""
        return await self._post(f"/api/players/{player_id}/shutdown/")
