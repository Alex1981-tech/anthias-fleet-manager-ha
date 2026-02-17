"""Config flow for Anthias Fleet Manager."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnthiasApiError, AnthiasAuthError, AnthiasFleetManagerApi
from .const import CONF_FM_URL, CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default="http://192.168.91.92:9000"): str,
        vol.Required(CONF_USERNAME, default="admin"): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class AnthiasFleetManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Anthias Fleet Manager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — FM URL + credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            fm_url = user_input[CONF_URL].rstrip("/")
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Set unique_id to prevent duplicate entries for the same FM
            await self.async_set_unique_id(fm_url)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            try:
                token = await AnthiasFleetManagerApi.async_get_token(
                    session, fm_url, username, password
                )
            except AnthiasAuthError:
                errors["base"] = "invalid_auth"
            except AnthiasApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Anthias FM ({fm_url})",
                    data={
                        CONF_FM_URL: fm_url,
                        CONF_TOKEN: token,
                        CONF_USERNAME: username,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
