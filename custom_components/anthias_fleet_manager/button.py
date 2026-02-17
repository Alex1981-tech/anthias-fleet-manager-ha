"""Button platform for Anthias Fleet Manager."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnthiasCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True, frozen=True)
class AnthiasButtonDescription(ButtonEntityDescription):
    """Describes an Anthias button entity."""

    press_fn_name: str


BUTTON_DESCRIPTIONS: tuple[AnthiasButtonDescription, ...] = (
    AnthiasButtonDescription(
        key="reboot",
        icon="mdi:restart",
        press_fn_name="async_reboot",
    ),
    AnthiasButtonDescription(
        key="shutdown",
        icon="mdi:power",
        press_fn_name="async_shutdown",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry."""
    coordinator: AnthiasCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AnthiasPlayerButton(coordinator, player_id, desc)
        for player_id in coordinator.data
        for desc in BUTTON_DESCRIPTIONS
    ]
    async_add_entities(entities)


class AnthiasPlayerButton(CoordinatorEntity[AnthiasCoordinator], ButtonEntity):
    """Button entity for a player action."""

    entity_description: AnthiasButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AnthiasCoordinator,
        player_id: str,
        description: AnthiasButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self._player_id = player_id
        self.entity_description = description
        player = coordinator.data[player_id]
        self._attr_unique_id = f"{player_id}_{description.key}"
        self._attr_name = (
            f"{player['name']} {description.key.replace('_', ' ').title()}"
        )

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

    async def async_press(self) -> None:
        """Handle button press."""
        fn = getattr(self.coordinator.api, self.entity_description.press_fn_name)
        await fn(self._player_id)
