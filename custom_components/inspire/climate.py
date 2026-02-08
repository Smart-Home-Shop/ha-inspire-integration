"""Climate platform for the Inspire integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FUNCTION_BOOST,
    FUNCTION_OFF,
    FUNCTION_ON,
    FUNCTION_PROGRAM_1,
    FUNCTION_PROGRAM_2,
    FUNCTION_BOTH_PROGRAMS,
    MAX_TEMP,
    MIN_TEMP,
    TEMP_STEP,
)
from .coordinator import InspireDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Map API Current_Function text to function constant
FUNCTION_TEXT_TO_VALUE: dict[str, int] = {
    "Off": FUNCTION_OFF,
    "Program 1": FUNCTION_PROGRAM_1,
    "Program 2": FUNCTION_PROGRAM_2,
    "Both": FUNCTION_BOTH_PROGRAMS,
    "On": FUNCTION_ON,
    "Boost": FUNCTION_BOOST,
}


def _is_thermostat(device: dict[str, Any]) -> bool:
    """Return True if device supports temperature/function control."""
    if device.get("Current_Temperature") is not None:
        return True
    unit_type = (device.get("Unit_Type") or "").strip()
    return unit_type in ("Roomstat", "TouchThermostat", "Wireless")


def _current_function_to_value(func_text: str | None) -> int:
    """Convert Current_Function string to FUNCTION_* constant."""
    if not func_text:
        return FUNCTION_OFF
    return FUNCTION_TEXT_TO_VALUE.get(func_text.strip(), FUNCTION_OFF)


def _effective_target_temperature(device: dict[str, Any]) -> float | None:
    """Get effective target temp from device info (On_Temperature vs Profile_Temperature)."""
    func = _current_function_to_value(device.get("Current_Function"))
    if func == FUNCTION_ON:
        raw = device.get("On_Temperature")
    else:
        raw = device.get("Profile_Temperature")
    if raw is None:
        raw = device.get("On_Temperature") or device.get("Profile_Temperature")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


class InspireClimateEntity(CoordinatorEntity[InspireDataUpdateCoordinator], ClimateEntity):
    """Climate entity for an Inspire thermostat."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.AUTO, HVACMode.OFF]
    _attr_max_temp = MAX_TEMP
    _attr_min_temp = MIN_TEMP
    _attr_target_temperature_step = TEMP_STEP
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = ["none", "boost"]

    def __init__(
        self,
        coordinator: InspireDataUpdateCoordinator,
        device_id: str,
        device_name: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._device_info = device_info
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{device_id}-climate"
        self._attr_name = device_name
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
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        dev = self._device
        if not dev:
            return None
        raw = dev.get("Current_Temperature")
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        dev = self._device
        if not dev:
            return None
        return _effective_target_temperature(dev)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        dev = self._device
        if not dev:
            return HVACMode.OFF
        func = _current_function_to_value(dev.get("Current_Function"))
        if func == FUNCTION_OFF:
            return HVACMode.OFF
        if func in (FUNCTION_PROGRAM_1, FUNCTION_PROGRAM_2, FUNCTION_BOTH_PROGRAMS):
            return HVACMode.AUTO
        return HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        """Return preset mode (boost or none)."""
        dev = self._device
        if not dev:
            return None
        func = _current_function_to_value(dev.get("Current_Function"))
        return "boost" if func == FUNCTION_BOOST else "none"

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        client = self.coordinator.client
        await client.set_temperature(self._device_id, float(temp))
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        client = self.coordinator.client
        if hvac_mode == HVACMode.OFF:
            await client.set_function(self._device_id, FUNCTION_OFF)
        elif hvac_mode == HVACMode.AUTO:
            await client.set_function(self._device_id, FUNCTION_PROGRAM_1)
        elif hvac_mode == HVACMode.HEAT:
            await client.set_function(self._device_id, FUNCTION_ON)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode (boost or none)."""
        if preset_mode == "boost":
            await self.coordinator.client.set_function(self._device_id, FUNCTION_BOOST)
        elif preset_mode == "none":
            await self.coordinator.client.set_function(self._device_id, FUNCTION_PROGRAM_1)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inspire climate entities from a config entry."""
    data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not data:
        return
    coordinator: InspireDataUpdateCoordinator = data["coordinator"]
    if not coordinator.data:
        return

    entities: list[InspireClimateEntity] = []
    for device in coordinator.data:
        device_id = device.get("device_id") or device.get("id")
        if not device_id or not _is_thermostat(device):
            continue
        name = device.get("name") or f"Thermostat {device_id}"
        entities.append(
            InspireClimateEntity(coordinator, device_id, name, device)
        )

    async_add_entities(entities)
