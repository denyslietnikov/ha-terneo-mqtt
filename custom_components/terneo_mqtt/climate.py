"""Climate platform for TerneoMQ integration."""
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
    """Set up TerneoMQ climate from a config entry."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.options.get("topic_prefix", config_entry.data.get("prefix", "terneo"))
    supports_air_temp = config_entry.options.get("supports_air_temp", True)
    entities = []
    for device in devices:
        client_id = device["client_id"]
        entities.append(TerneoMQTTClimate(hass, client_id, prefix, supports_air_temp))
    if entities:
        async_add_entities(entities)


class TerneoMQTTClimate(ClimateEntity):
    """Representation of a TerneoMQ climate device."""

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

    def __init__(self, hass: HomeAssistant, client_id: str, topic_prefix: str, supports_air_temp: bool = True, state_topic: str = None, command_topic: str = None) -> None:
        """Initialize the climate device."""
        self.hass = hass
        self._client_id = client_id
        self._topic_prefix = topic_prefix
        self._supports_air_temp = supports_air_temp
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
        self._mode_topic = f"{topic_prefix}/{client_id}/mode"
        self._attr_unique_id = f"terneo_{client_id}"
        self._attr_name = f"Terneo {client_id}"
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._floor_temp = None
        self._power_off = None
        self._load = None
        self._mode = None  # 0 = auto, 1 = manual

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics."""
        await super().async_added_to_hass()
        if self._supports_air_temp:
            self._unsub_air_temp = await mqtt.async_subscribe(
                self.hass, self._air_temp_topic, self._handle_message, 0
            )
            self.async_on_remove(self._unsub_air_temp)
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
        self._unsub_mode = await mqtt.async_subscribe(
            self.hass, self._mode_topic, self._handle_message, 0
        )
        self.async_on_remove(self._unsub_floor_temp)
        self.async_on_remove(self._unsub_set_temp)
        self.async_on_remove(self._unsub_load)
        self.async_on_remove(self._unsub_power_off)
        self.async_on_remove(self._unsub_mode)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topics."""
        await super().async_will_remove_from_hass()

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
                updated = True
            elif msg.topic == self._load_topic:
                self._load = int(msg.payload)
                self._update_hvac_mode_from_temps()
                updated = True
            elif msg.topic == self._power_off_topic:
                self._power_off = int(msg.payload)
                self._update_hvac_mode_from_temps()
                updated = True
            elif msg.topic == self._mode_topic:
                self._mode = int(msg.payload)
                self._update_hvac_mode_from_temps()
                updated = True
            
            if updated:
                self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid payload in message: %s", msg.payload)

    def _update_hvac_mode_from_temps(self) -> None:
        """Update hvac_mode and hvac_action based on powerOff, load and mode."""
        # hvac_mode is based on powerOff, load and mode
        if self._power_off == 1:
            self._attr_hvac_mode = climate.HVACMode.OFF
            self._attr_hvac_action = climate.HVACAction.OFF
        else:
            # If actively heating (load=1), show HEAT regardless of mode
            if self._load == 1:
                self._attr_hvac_mode = climate.HVACMode.HEAT
            else:
                # Check if mode is available
                if self._mode == 0:
                    self._attr_hvac_mode = climate.HVACMode.AUTO
                else:
                    self._attr_hvac_mode = climate.HVACMode.HEAT
            
            # hvac_action based on load
            if self._load == 1:
                self._attr_hvac_action = climate.HVACAction.HEATING
            else:
                self._attr_hvac_action = climate.HVACAction.IDLE
        
        # Fallback: if no airTemp but have floorTemp, use floorTemp as current temp
        if self._attr_current_temperature is None and self._floor_temp is not None:
            self._attr_current_temperature = self._floor_temp

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.debug("Setting temperature to %s", temperature)
            # If currently OFF, switch to HEAT when setting temperature
            if self._attr_hvac_mode == climate.HVACMode.OFF:
                _LOGGER.debug("Switching to HEAT mode for temperature setting")
                self._attr_hvac_mode = climate.HVACMode.HEAT
                await mqtt.async_publish(self.hass, self._power_off_cmd_topic, "0", retain=True)
            await mqtt.async_publish(self.hass, self._set_temp_cmd_topic, str(temperature), retain=True)
            # Optimistically update the state
            self._attr_target_temperature = temperature
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new HVAC mode."""
        _LOGGER.debug("Setting HVAC mode to %s", hvac_mode)
        if hvac_mode == climate.HVACMode.HEAT:
            # Set to manual mode and turn on
            await mqtt.async_publish(self.hass, self._power_off_cmd_topic, "0", retain=True)
            await mqtt.async_publish(self.hass, self._mode_cmd_topic, "1", retain=True)
        elif hvac_mode == climate.HVACMode.AUTO:
            # Set to auto mode and turn on
            await mqtt.async_publish(self.hass, self._power_off_cmd_topic, "0", retain=True)
            await mqtt.async_publish(self.hass, self._mode_cmd_topic, "0", retain=True)
        elif hvac_mode == climate.HVACMode.OFF:
            await mqtt.async_publish(self.hass, self._power_off_cmd_topic, "1", retain=True)
        else:
            return
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