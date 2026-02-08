"""Inspire integration."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InspireAPIClient
from .const import CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import InspireDataUpdateCoordinator
from .services import async_setup_services


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Inspire from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    client = InspireAPIClient(
        api_key=config_entry.data[CONF_API_KEY],
        username=config_entry.data[CONF_USERNAME],
        password=config_entry.data[CONF_PASSWORD],
        session=session,
    )

    coordinator = InspireDataUpdateCoordinator(hass, client, config_entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except config_entries.ConfigEntryAuthFailed:
        raise
    except Exception:
        raise config_entries.ConfigEntryNotReady from None

    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
    }

    async_setup_services(hass)

    await hass.config_entries.async_forward_entry_setups(
        config_entry, ["climate", "sensor"]
    )
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload an Inspire config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(
        config_entry, "climate"
    )
    unload_ok = await hass.config_entries.async_forward_entry_unload(
        config_entry, "sensor"
    ) and unload_ok

    if unload_ok:
        data = hass.data[DOMAIN].pop(config_entry.entry_id, None)
        if data and "client" in data:
            await data["client"].close()

    return unload_ok
