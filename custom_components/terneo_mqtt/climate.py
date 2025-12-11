"""Climate platform for Terneo MQTT integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import climate, mqtt
from homeassistant.components.climate import ClimateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Terneo MQTT climate from a config entry."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.data.get("prefix", "terneo")
    entities = []
    for device in devices:
        client_id = device["client_id"]
        entities.append(TerneoMQTTClimate(hass, client_id, prefix))
    if entities:
        async_add_entities(entities)


class TerneoMQTTClimate(ClimateEntity):
    """Representation of a Terneo MQTT climate device."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        climate.ClimateEntityFeature.TARGET_TEMPERATURE
        | climate.ClimateEntityFeature.TURN_OFF
        | climate.ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = [climate.HVACMode.HEAT, climate.HVACMode.OFF, climate.HVACMode.AUTO]
    _attr_hvac_mode = climate.HVACMode.OFF
    _attr_hvac_action = climate.HVACAction.OFF
    _attr_min_temp = 5
    _attr_max_temp = 35
    _attr_precision = 0.5

    def __init__(self, hass: HomeAssistant, client_id: str, topic_prefix: str, state_topic: str = None, command_topic: str = None) -> None:
        """Initialize the climate device."""
        self.hass = hass
        self._client_id = client_id
        self._topic_prefix = topic_prefix
        # Status topics
        self._air_temp_topic = f"{topic_prefix}/{client_id}/airTemp"
        self._floor_temp_topic = f"{topic_prefix}/{client_id}/floorTemp"
        self._set_temp_topic = f"{topic_prefix}/{client_id}/setTemp"
        self._load_topic = f"{topic_prefix}/{client_id}/load"
        self._power_off_topic = f"{topic_prefix}/{client_id}/powerOff"
        # Command topics
        self._set_temp_cmd_topic = f"{topic_prefix}/{client_id}/setTemp"
        self._power_off_cmd_topic = f"{topic_prefix}/{client_id}/powerOff"
        self._mode_cmd_topic = f"{topic_prefix}/{client_id}/mode"
        self._attr_unique_id = f"terneo_{client_id}"
        self._attr_name = f"Terneo {client_id}"
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._floor_temp = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics."""
        self._unsub_air_temp = await mqtt.async_subscribe(
            self.hass, self._air_temp_topic, self._handle_message, 0
        )
        self._unsub_floor_temp = await mqtt.async_subscribe(
            self.hass, self._floor_temp_topic, self._handle_message, 0
        )
        self._unsub_set_temp = await mqtt.async_subscribe(
            self.hass, self._set_temp_topic, self._handle_message, 0
        )
        self._unsub_load = await mqtt.async_subscribe(
            self.hass, self._load_topic, self._handle_message, 0
        )
        self._unsub_power_off = await mqtt.async_subscribe(
            self.hass, self._power_off_topic, self._handle_message, 0
        )
        self.async_on_remove(self._unsub_air_temp)
        self.async_on_remove(self._unsub_floor_temp)
        self.async_on_remove(self._unsub_set_temp)
        self.async_on_remove(self._unsub_load)
        self.async_on_remove(self._unsub_power_off)

    @callback
    def _handle_message(self, msg) -> None:
        """Handle status message from MQTT."""
        _LOGGER.debug("Received MQTT message: %s %s", msg.topic, msg.payload)
        try:
            updated = False
            if msg.topic == self._air_temp_topic:
                self._attr_current_temperature = float(msg.payload)
                updated = True
            elif msg.topic == self._floor_temp_topic:
                self._floor_temp = float(msg.payload)
                # Update hvac_mode based on setTemp vs floorTemp
                self._update_hvac_mode_from_temps()
                updated = True
            elif msg.topic == self._set_temp_topic:
                self._attr_target_temperature = float(msg.payload)
                # Update hvac_mode based on setTemp vs floorTemp
                self._update_hvac_mode_from_temps()
                updated = True
            elif msg.topic == self._load_topic:
                # Update hvac_action based on load, but only if power is ON (powerOff=0)
                # HEATING: load=1 (implies powerOff=0) → orange ring
                # IDLE: load=0 and powerOff=0 → green ring
                if self._attr_hvac_mode == climate.HVACMode.HEAT:
                    self._attr_hvac_action = (
                        climate.HVACAction.HEATING if msg.payload == "1" else climate.HVACAction.IDLE
                    )
                updated = True
            elif msg.topic == self._power_off_topic:
                old_hvac_mode = self._attr_hvac_mode
                self._attr_hvac_mode = (
                    climate.HVACMode.OFF if msg.payload == "1" else 
                    (climate.HVACMode.AUTO if old_hvac_mode == climate.HVACMode.AUTO else climate.HVACMode.HEAT)
                )
                # Update hvac_action based on new hvac_mode
                if self._attr_hvac_mode == climate.HVACMode.OFF:
                    # OFF: powerOff=1 → gray ring
                    self._attr_hvac_action = climate.HVACAction.OFF
                else:
                    # Power ON: assume IDLE initially (will be updated by load message)
                    # IDLE: powerOff=0 and load=0 → green ring
                    self._attr_hvac_action = climate.HVACAction.IDLE
                updated = True
            
            if updated:
                self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid payload in message: %s", msg.payload)

    def _update_hvac_mode_from_temps(self) -> None:
        """Update hvac_mode based on setTemp vs floorTemp."""
        # Don't change mode if thermostat is OFF
        if self._attr_hvac_mode == climate.HVACMode.OFF:
            return
        if self._attr_target_temperature is not None and self._floor_temp is not None:
            if self._attr_target_temperature > self._floor_temp:
                self._attr_hvac_mode = climate.HVACMode.HEAT
            else:
                self._attr_hvac_mode = climate.HVACMode.AUTO
            # Update hvac_action accordingly
            if self._attr_hvac_mode == climate.HVACMode.OFF:
                self._attr_hvac_action = climate.HVACAction.OFF
            else:
                # For AUTO/HEAT, action depends on load, but assume IDLE initially
                self._attr_hvac_action = climate.HVACAction.IDLE

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.debug("Setting temperature to %s", temperature)
            # If currently OFF or AUTO, switch to HEAT when setting temperature
            if self._attr_hvac_mode in (climate.HVACMode.OFF, climate.HVACMode.AUTO):
                _LOGGER.debug("Switching to HEAT mode for temperature setting")
                self._attr_hvac_mode = climate.HVACMode.HEAT
                await mqtt.async_publish(self.hass, self._power_off_cmd_topic, "0", retain=True)
            await mqtt.async_publish(self.hass, self._set_temp_cmd_topic, str(temperature), retain=True)
            # Switch to manual mode when temperature is set manually
            await mqtt.async_publish(self.hass, self._mode_cmd_topic, "1", retain=True)
            # Optimistically update the state
            self._attr_target_temperature = temperature
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new HVAC mode."""
        _LOGGER.debug("Setting HVAC mode to %s", hvac_mode)
        if hvac_mode == climate.HVACMode.HEAT:
            payload = "0"
        elif hvac_mode == climate.HVACMode.AUTO:
            payload = "0"  # Turn on
        elif hvac_mode == climate.HVACMode.OFF:
            payload = "1"
        else:
            return
        _LOGGER.debug("Publishing to %s payload %s", self._power_off_cmd_topic, payload)
        await mqtt.async_publish(self.hass, self._power_off_cmd_topic, payload, retain=True)
        # Optimistically update the state
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._client_id)},
            "name": f"Terneo {self._client_id}",
            "manufacturer": "Terneo",
            "model": "AX",
        }