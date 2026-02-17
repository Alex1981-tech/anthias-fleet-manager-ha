"""Service handlers for Anthias Fleet Manager."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import AnthiasCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_DEPLOY_CONTENT = "deploy_content"
SERVICE_CREATE_ASSET = "create_asset"
SERVICE_DELETE_ASSET = "delete_asset"
SERVICE_TOGGLE_ASSET = "toggle_asset"
SERVICE_CREATE_SCHEDULE_SLOT = "create_schedule_slot"
SERVICE_DELETE_SCHEDULE_SLOT = "delete_schedule_slot"
SERVICE_ADD_SLOT_ITEM = "add_slot_item"
SERVICE_REMOVE_SLOT_ITEM = "remove_slot_item"
SERVICE_TRIGGER_UPDATE = "trigger_update"


def _get_coordinator(hass: HomeAssistant) -> AnthiasCoordinator:
    """Get the first available coordinator."""
    coordinators = hass.data.get(DOMAIN, {})
    if not coordinators:
        raise ValueError("No Anthias Fleet Manager integration configured")
    return next(iter(coordinators.values()))


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Anthias Fleet Manager services."""

    async def handle_deploy_content(call: ServiceCall) -> None:
        """Handle deploy_content service call."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.async_deploy_content(
            {
                "player_id": call.data["player_id"],
                "media_file_id": call.data["media_file_id"],
            }
        )

    async def handle_create_asset(call: ServiceCall) -> None:
        """Handle create_asset service call."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.async_create_asset(
            call.data["player_id"],
            {
                "name": call.data["name"],
                "uri": call.data["uri"],
                "duration": str(call.data["duration"]),
                "mimetype": call.data["mimetype"],
            },
        )

    async def handle_delete_asset(call: ServiceCall) -> None:
        """Handle delete_asset service call."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.async_delete_asset(
            call.data["player_id"],
            call.data["asset_id"],
        )

    async def handle_toggle_asset(call: ServiceCall) -> None:
        """Handle toggle_asset service call."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.async_update_asset(
            call.data["player_id"],
            {
                "asset_id": call.data["asset_id"],
                "is_enabled": call.data["is_enabled"],
            },
        )

    async def handle_create_schedule_slot(call: ServiceCall) -> None:
        """Handle create_schedule_slot service call."""
        coordinator = _get_coordinator(hass)
        data: dict = {
            "slot_type": call.data["slot_type"],
            "name": call.data["name"],
        }
        if "start_time" in call.data:
            data["start_time"] = str(call.data["start_time"])
        if "end_time" in call.data:
            data["end_time"] = str(call.data["end_time"])
        if "days_of_week" in call.data:
            days_str = call.data["days_of_week"]
            data["days_of_week"] = [int(d.strip()) for d in days_str.split(",") if d.strip()]
        await coordinator.api.async_create_schedule_slot(
            call.data["player_id"], data
        )

    async def handle_delete_schedule_slot(call: ServiceCall) -> None:
        """Handle delete_schedule_slot service call."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.async_delete_schedule_slot(
            call.data["player_id"],
            call.data["slot_id"],
        )

    async def handle_add_slot_item(call: ServiceCall) -> None:
        """Handle add_slot_item service call."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.async_add_slot_item(
            call.data["player_id"],
            call.data["slot_id"],
            call.data["asset_id"],
        )

    async def handle_remove_slot_item(call: ServiceCall) -> None:
        """Handle remove_slot_item service call."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.async_remove_slot_item(
            call.data["player_id"],
            call.data["slot_id"],
            call.data["item_id"],
        )

    async def handle_trigger_update(call: ServiceCall) -> None:
        """Handle trigger_update service call."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.async_trigger_update(call.data["player_id"])

    hass.services.async_register(
        DOMAIN,
        SERVICE_DEPLOY_CONTENT,
        handle_deploy_content,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
                vol.Required("media_file_id"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_ASSET,
        handle_create_asset,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
                vol.Required("name"): cv.string,
                vol.Required("uri"): cv.string,
                vol.Required("duration", default=10): vol.Coerce(int),
                vol.Required("mimetype", default="webpage"): vol.In(
                    ["webpage", "image", "video"]
                ),
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_ASSET,
        handle_delete_asset,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
                vol.Required("asset_id"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TOGGLE_ASSET,
        handle_toggle_asset,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
                vol.Required("asset_id"): cv.string,
                vol.Required("is_enabled", default=True): cv.boolean,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_SCHEDULE_SLOT,
        handle_create_schedule_slot,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
                vol.Required("slot_type", default="default"): vol.In(
                    ["default", "time", "event"]
                ),
                vol.Required("name"): cv.string,
                vol.Optional("start_time"): cv.string,
                vol.Optional("end_time"): cv.string,
                vol.Optional("days_of_week"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_SCHEDULE_SLOT,
        handle_delete_schedule_slot,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
                vol.Required("slot_id"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_SLOT_ITEM,
        handle_add_slot_item,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
                vol.Required("slot_id"): cv.string,
                vol.Required("asset_id"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_SLOT_ITEM,
        handle_remove_slot_item,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
                vol.Required("slot_id"): cv.string,
                vol.Required("item_id"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRIGGER_UPDATE,
        handle_trigger_update,
        schema=vol.Schema(
            {
                vol.Required("player_id"): cv.string,
            }
        ),
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Anthias Fleet Manager services."""
    for service in (
        SERVICE_DEPLOY_CONTENT,
        SERVICE_CREATE_ASSET,
        SERVICE_DELETE_ASSET,
        SERVICE_TOGGLE_ASSET,
        SERVICE_CREATE_SCHEDULE_SLOT,
        SERVICE_DELETE_SCHEDULE_SLOT,
        SERVICE_ADD_SLOT_ITEM,
        SERVICE_REMOVE_SLOT_ITEM,
        SERVICE_TRIGGER_UPDATE,
    ):
        hass.services.async_remove(DOMAIN, service)
