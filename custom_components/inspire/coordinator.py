"""DataUpdateCoordinator for the Inspire integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    InspireAPIClient,
    InspireAuthError,
    InspireConnectionError,
    InspireDeviceError,
)
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
        self._summary: dict[str, Any] = {}

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch devices and their info from the API."""
        _LOGGER.debug("Refresh started")
        try:
            if not self._device_list:
                self._device_list = await self.client.get_devices()
                _LOGGER.debug("Fetched %d devices", len(self._device_list))
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
            except asyncio.CancelledError:
                raise
            except (InspireConnectionError, Exception) as err:
                _LOGGER.warning(
                    "Failed to get info for device %s: %s",
                    device_id,
                    err,
                )
                merged = {**device, "device_id": device_id}
                result.append(merged)

        _LOGGER.debug("Fetched info for %d devices", len(result))
        try:
            self._summary = await self.client.get_summary()
            _LOGGER.debug("Summary: %d keys", len(self._summary))
        except asyncio.CancelledError:
            self._summary = {}
            # Don't re-raise: allow setup to complete with device data
        except InspireDeviceError:
            # API sometimes returns "Invalid Device ID" for get_summary; treat as no summary
            self._summary = {}
        except Exception as err:
            _LOGGER.debug("Failed to fetch summary: %s", err)
            self._summary = {}

        _LOGGER.info("Refresh complete: %d devices", len(result))
        return result
