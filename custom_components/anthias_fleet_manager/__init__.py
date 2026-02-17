"""Anthias Fleet Manager integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnthiasFleetManagerApi
from .const import CONF_FM_URL, CONF_TOKEN, DOMAIN, PLATFORMS
from .coordinator import AnthiasCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Anthias Fleet Manager from a config entry."""
    session = async_get_clientsession(hass)
    api = AnthiasFleetManagerApi(
        session=session,
        base_url=entry.data[CONF_FM_URL],
        token=entry.data[CONF_TOKEN],
    )

    coordinator = AnthiasCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services when the first entry is set up
    if len(hass.data[DOMAIN]) == 1:
        await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Unload services when the last entry is removed
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
    return unload_ok
