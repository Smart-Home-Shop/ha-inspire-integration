"""Config flow for the Inspire integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InspireAPIClient, InspireAuthError, InspireConnectionError
from .const import CONF_API_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class InspireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Inspire."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the credentials by attempting to connect
            try:
                session = async_get_clientsession(self.hass)
                client = InspireAPIClient(
                    api_key=user_input[CONF_API_KEY],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=session,
                )
                
                # Test connection
                await client.connect()
                
                # Get devices to verify API access
                devices = await client.get_devices()
                
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    # Create entry with username as the title
                    return self.async_create_entry(
                        title=f"Inspire ({user_input[CONF_USERNAME]})",
                        data=user_input,
                    )

            except InspireAuthError:
                errors["base"] = "invalid_auth"
            except InspireConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during setup")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )
