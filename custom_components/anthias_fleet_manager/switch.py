"""Switch platform for Anthias Fleet Manager — CEC display power."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
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
    """Set up CEC switch entities from a config entry."""
    coordinator: AnthiasCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for player_id, player_data in coordinator.data.items():
        cec = player_data.get("cec", {})
        if cec.get("cec_available"):
            entities.append(AnthiasDisplaySwitch(coordinator, player_id))

    async_add_entities(entities)


class AnthiasDisplaySwitch(CoordinatorEntity[AnthiasCoordinator], SwitchEntity):
    """Switch to control TV power via CEC."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_has_entity_name = True
    _attr_icon = "mdi:television"

    def __init__(self, coordinator: AnthiasCoordinator, player_id: str) -> None:
        super().__init__(coordinator)
        self._player_id = player_id
        player = coordinator.data[player_id]
        self._attr_unique_id = f"{player_id}_display"
        self._attr_name = f"{player['name']} Display"

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
    def is_on(self) -> bool | None:
        """Return True if the TV is on (CEC reports power on)."""
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        cec = player.get("cec", {})
        return cec.get("tv_on", False)

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return False
        return player.get("is_online", False) and player.get("cec", {}).get("cec_available", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Wake TV via CEC."""
        try:
            await self.coordinator.api.async_cec_wake(self._player_id)
        except AnthiasApiError as err:
            _LOGGER.error("Failed to wake display for %s: %s", self._player_id, err)
            return
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Send TV to standby via CEC."""
        try:
            await self.coordinator.api.async_cec_standby(self._player_id)
        except AnthiasApiError as err:
            _LOGGER.error("Failed to standby display for %s: %s", self._player_id, err)
            return
        await self.coordinator.async_request_refresh()
