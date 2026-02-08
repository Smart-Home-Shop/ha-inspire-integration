"""DataUpdateCoordinator for the Inspire integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import InspireAPIClient, InspireAuthError, InspireConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class InspireDataUpdateCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator that fetches device list and device info from the Inspire API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: InspireAPIClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.config_entry = config_entry
        self._device_list: list[dict[str, Any]] = []

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch devices and their info from the API."""
        try:
            if not self._device_list:
                self._device_list = await self.client.get_devices()
                if not self._device_list:
                    return []
        except InspireAuthError:
            raise config_entries.ConfigEntryAuthFailed from None
        except Exception as err:
            _LOGGER.exception("Failed to fetch devices: %s", err)
            raise

        result: list[dict[str, Any]] = []
        for device in self._device_list:
            device_id = device.get("device_id") or device.get("id")
            if not device_id:
                continue
            try:
                info = await self.client.get_device_information(device_id)
                merged = {**device, **info}
                merged["device_id"] = device_id
                result.append(merged)
            except InspireAuthError:
                raise config_entries.ConfigEntryAuthFailed from None
            except (InspireConnectionError, Exception) as err:
                _LOGGER.warning(
                    "Failed to get info for device %s: %s",
                    device_id,
                    err,
                )
                merged = {**device, "device_id": device_id}
                result.append(merged)

        return result
