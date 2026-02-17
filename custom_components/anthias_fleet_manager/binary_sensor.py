"""Binary sensor platform for Anthias Fleet Manager."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnthiasCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""
    coordinator: AnthiasCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AnthiasPlayerOnlineSensor(coordinator, player_id)
        for player_id in coordinator.data
    ]
    async_add_entities(entities)


class AnthiasPlayerOnlineSensor(CoordinatorEntity[AnthiasCoordinator], BinarySensorEntity):
    """Binary sensor: player online/offline."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True
    _attr_translation_key = "online"

    def __init__(self, coordinator: AnthiasCoordinator, player_id: str) -> None:
        super().__init__(coordinator)
        self._player_id = player_id
        player = coordinator.data[player_id]
        self._attr_unique_id = f"{player_id}_online"
        self._attr_name = f"{player['name']} Online"

    @property
    def device_info(self):
        """Return device info for this player."""
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
        """Return True if the player is online."""
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        return player.get("is_online", False)

    @property
    def available(self) -> bool:
        """Entity is available as long as the coordinator gets data."""
        return (
            self.coordinator.last_update_success
            and self._player_id in self.coordinator.data
        )
