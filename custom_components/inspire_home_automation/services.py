"""Service handlers for the Inspire integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    SERVICE_SCHEDULE_HEATING_START,
    SERVICE_CANCEL_SCHEDULED_START,
    SERVICE_ADVANCE_PROGRAM,
    SERVICE_SYNC_DEVICE_TIME,
    SERVICE_SET_PROGRAM_SCHEDULE,
    SERVICE_SET_PROGRAM_TYPE,
)

_LOGGER = logging.getLogger(__name__)


def _get_client_and_coordinator(
    hass: HomeAssistant, device_id: str
) -> tuple[Any, Any] | None:
    """Return (client, coordinator) for the given device_id, or None."""
    domain_data = hass.data.get(DOMAIN) or {}
    for entry_id, data in domain_data.items():
        if entry_id.startswith("_"):
            continue
        if not isinstance(data, dict):
            continue
        coordinator = data.get("coordinator")
        client = data.get("client")
        if not coordinator or not client or not coordinator.data:
            continue
        for device in coordinator.data:
            if (device.get("device_id") or device.get("id")) == device_id:
                return (client, coordinator)
    return None


async def schedule_heating_start(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle schedule_heating_start service."""
    device_id = call.data["device_id"]
    datetime_str = call.data["datetime"]
    result = _get_client_and_coordinator(hass, device_id)
    if not result:
        _LOGGER.error("Device %s not found", device_id)
        return
    client, coordinator = result
    await client.set_scheduled_start(device_id, datetime_str)
    await coordinator.async_request_refresh()


async def cancel_scheduled_start(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle cancel_scheduled_start service."""
    device_id = call.data["device_id"]
    result = _get_client_and_coordinator(hass, device_id)
    if not result:
        _LOGGER.error("Device %s not found", device_id)
        return
    client, coordinator = result
    await client.cancel_scheduled_start(device_id)
    await coordinator.async_request_refresh()


async def advance_program(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle advance_program service."""
    device_id = call.data["device_id"]
    result = _get_client_and_coordinator(hass, device_id)
    if not result:
        _LOGGER.error("Device %s not found", device_id)
        return
    client, coordinator = result
    await client.set_advance(device_id)
    await coordinator.async_request_refresh()


async def sync_device_time(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle sync_device_time service."""
    device_id = call.data["device_id"]
    time_str = call.data["time"]
    result = _get_client_and_coordinator(hass, device_id)
    if not result:
        _LOGGER.error("Device %s not found", device_id)
        return
    client, coordinator = result
    await client.set_time(device_id, time_str)
    await coordinator.async_request_refresh()


async def set_program_schedule(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle set_program_schedule service."""
    device_id = call.data["device_id"]
    program = int(call.data["program"])
    day = int(call.data["day"])
    period = int(call.data["period"])
    time_str = str(call.data["time"])
    temperature = float(call.data["temperature"])
    result = _get_client_and_coordinator(hass, device_id)
    if not result:
        _LOGGER.error("Device %s not found", device_id)
        return
    client, coordinator = result
    await client.set_program_time(
        device_id, program, day, period, time_str, temperature
    )
    await coordinator.async_request_refresh()


async def set_program_type(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle set_program_type service."""
    device_id = call.data["device_id"]
    program_type = call.data["program_type"]
    result = _get_client_and_coordinator(hass, device_id)
    if not result:
        _LOGGER.error("Device %s not found", device_id)
        return
    client, coordinator = result
    await client.set_pgmtype(device_id, program_type)
    await coordinator.async_request_refresh()


def async_setup_services(hass: HomeAssistant) -> bool:
    """Register Inspire services. Returns True if newly registered."""
    if hass.data.get(DOMAIN, {}).get("_services_registered"):
        return False

    schema_schedule = vol.Schema(
        {
            vol.Required("device_id"): cv.string,
            vol.Required("datetime"): cv.string,
        }
    )
    schema_device = vol.Schema({vol.Required("device_id"): cv.string})
    schema_sync_time = vol.Schema(
        {
            vol.Required("device_id"): cv.string,
            vol.Required("time"): cv.string,
        }
    )
    schema_program_schedule = vol.Schema(
        {
            vol.Required("device_id"): cv.string,
            vol.Required("program"): vol.All(vol.Coerce(int), vol.Range(1, 2)),
            vol.Required("day"): vol.All(vol.Coerce(int), vol.Range(0, 6)),
            vol.Required("period"): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Required("time"): cv.string,
            vol.Required("temperature"): vol.All(
                vol.Coerce(float), vol.Range(10.0, 30.0)
            ),
        }
    )
    schema_program_type = vol.Schema(
        {
            vol.Required("device_id"): cv.string,
            vol.Required("program_type"): cv.string,
        }
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHEDULE_HEATING_START,
        schedule_heating_start,
        schema=schema_schedule,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_SCHEDULED_START,
        cancel_scheduled_start,
        schema=schema_device,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADVANCE_PROGRAM,
        advance_program,
        schema=schema_device,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_DEVICE_TIME,
        sync_device_time,
        schema=schema_sync_time,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PROGRAM_SCHEDULE,
        set_program_schedule,
        schema=schema_program_schedule,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PROGRAM_TYPE,
        set_program_type,
        schema=schema_program_type,
    )

    hass.data.setdefault(DOMAIN, {})["_services_registered"] = True
    return True
