"""Sensor platform for the Inspire integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import InspireDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _is_thermostat(device: dict[str, Any]) -> bool:
    """Return True if device has current temperature."""
    return device.get("Current_Temperature") is not None


def _has_battery(device: dict[str, Any]) -> bool:
    """Return True if device has battery info."""
    return (
        device.get("Battery") is not None
        or device.get("Battery_Voltage") is not None
    )


class InspireTemperatureSensor(
    CoordinatorEntity[InspireDataUpdateCoordinator], SensorEntity
):
    """Temperature sensor for an Inspire device."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: InspireDataUpdateCoordinator,
        device_id: str,
        device_name: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{device_id}-temperature"
        self._attr_name = "Temperature"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_name,
            "manufacturer": "Inspire Home Automation",
            "model": device_info.get("Unit_Model"),
        }

    @property
    def _device(self) -> dict[str, Any] | None:
        """Return merged device data from coordinator."""
        if not self.coordinator.data:
            return None
        for d in self.coordinator.data:
            if (d.get("device_id") or d.get("id")) == self._device_id:
                return d
        return None

    @property
    def native_value(self) -> float | None:
        """Return current temperature."""
        dev = self._device
        if not dev:
            return None
        raw = dev.get("Current_Temperature")
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None


class InspireBatterySensor(
    CoordinatorEntity[InspireDataUpdateCoordinator], SensorEntity
):
    """Battery status sensor for an Inspire device (API returns 'OK' / 'Low' or voltage, not %)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: InspireDataUpdateCoordinator,
        device_id: str,
        device_name: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{device_id}-battery"
        self._attr_name = "Battery"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_name,
            "manufacturer": "Inspire Home Automation",
            "model": device_info.get("Unit_Model"),
        }

    @property
    def _device(self) -> dict[str, Any] | None:
        """Return merged device data from coordinator."""
        if not self.coordinator.data:
            return None
        for d in self.coordinator.data:
            if (d.get("device_id") or d.get("id")) == self._device_id:
                return d
        return None

    @property
    def native_value(self) -> str | None:
        """Return battery status (OK / Low) or voltage string."""
        dev = self._device
        if not dev:
            return None
        battery = dev.get("Battery")
        if battery is not None:
            return str(battery).strip() or None
        voltage = dev.get("Battery_Voltage")
        if voltage is not None:
            return str(voltage)
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inspire sensors from a config entry."""
    data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not data:
        return
    coordinator: InspireDataUpdateCoordinator = data["coordinator"]
    if not coordinator.data:
        return

    entities: list[SensorEntity] = []
    for device in coordinator.data:
        device_id = device.get("device_id") or device.get("id")
        if not device_id:
            continue
        name = device.get("name") or f"Device {device_id}"
        if _is_thermostat(device):
            entities.append(
                InspireTemperatureSensor(coordinator, device_id, name, device)
            )
        if _has_battery(device):
            entities.append(
                InspireBatterySensor(coordinator, device_id, name, device)
            )

    async_add_entities(entities)
