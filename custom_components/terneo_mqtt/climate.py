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
    serial = config_entry.data.get("serial")
    topic_prefix = config_entry.options.get("topic_prefix", config_entry.data.get("topic_prefix", "terneo"))
    if serial:
        async_add_entities([TerneoMQTTClimate(hass, serial, topic_prefix)])


class TerneoMQTTClimate(ClimateEntity):
    """Representation of a Terneo MQTT climate device."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        climate.ClimateEntityFeature.TARGET_TEMPERATURE
        | climate.ClimateEntityFeature.TURN_OFF
        | climate.ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = [climate.HVACMode.HEAT, climate.HVACMode.OFF]
    _attr_hvac_mode = climate.HVACMode.OFF
    _attr_min_temp = 5
    _attr_max_temp = 35
    _attr_precision = 0.5

    def __init__(self, hass: HomeAssistant, serial: str, topic_prefix: str, state_topic: str = None, command_topic: str = None) -> None:
        """Initialize the climate device."""
        self.hass = hass
        self._serial = serial
        self._topic_prefix = topic_prefix
        # Status topics
        self._air_temp_topic = f"{topic_prefix}/{serial}/airTemp"
        self._set_temp_topic = f"{topic_prefix}/{serial}/setTemp"
        self._load_topic = f"{topic_prefix}/{serial}/load"
        # Command topics
        self._set_temp_cmd_topic = f"{topic_prefix}/{serial}/setTemp"
        self._power_off_cmd_topic = f"{topic_prefix}/{serial}/powerOff"
        self._attr_unique_id = f"terneo_{serial}"
        self._attr_name = f"Terneo {serial}"
        self._attr_current_temperature = None
        self._attr_target_temperature = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics."""
        self._unsub_air_temp = await mqtt.async_subscribe(
            self.hass, self._air_temp_topic, self._handle_message, 0
        )
        self._unsub_set_temp = await mqtt.async_subscribe(
            self.hass, self._set_temp_topic, self._handle_message, 0
        )
        self._unsub_load = await mqtt.async_subscribe(
            self.hass, self._load_topic, self._handle_message, 0
        )
        self.async_on_remove(self._unsub_air_temp)
        self.async_on_remove(self._unsub_set_temp)
        self.async_on_remove(self._unsub_load)

    @callback
    def _handle_message(self, msg) -> None:
        """Handle status message from MQTT."""
        _LOGGER.debug("Received MQTT message: %s %s", msg.topic, msg.payload)
        try:
            if msg.topic == self._air_temp_topic:
                self._attr_current_temperature = float(msg.payload.decode())
            elif msg.topic == self._set_temp_topic:
                self._attr_target_temperature = float(msg.payload.decode())
            elif msg.topic == self._load_topic:
                self._attr_hvac_mode = (
                    climate.HVACMode.OFF if msg.payload.decode() == "0" else climate.HVACMode.HEAT
                )
            self.async_write_ha_state()
        except (ValueError, UnicodeDecodeError):
            _LOGGER.error("Invalid payload in message: %s", msg.payload)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.debug("Setting temperature to %s", temperature)
            # If currently OFF, turn on to HEAT when setting temperature
            if self._attr_hvac_mode == climate.HVACMode.OFF:
                _LOGGER.debug("Switching to HEAT mode for temperature setting")
                self._attr_hvac_mode = climate.HVACMode.HEAT
                await mqtt.async_publish(self.hass, self._power_off_cmd_topic, "0")
            await mqtt.async_publish(self.hass, self._set_temp_cmd_topic, str(temperature))
            # Optimistically update the state
            self._attr_target_temperature = temperature
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new HVAC mode."""
        _LOGGER.debug("Setting HVAC mode to %s", hvac_mode)
        if hvac_mode == climate.HVACMode.HEAT:
            payload = "0"
            # Set default target temperature if not set
            if self._attr_target_temperature is None:
                self._attr_target_temperature = 20.0
                await mqtt.async_publish(self.hass, self._set_temp_cmd_topic, "20.0")
        elif hvac_mode == climate.HVACMode.OFF:
            payload = "1"
        else:
            return
        _LOGGER.debug("Publishing to %s payload %s", self._power_off_cmd_topic, payload)
        await mqtt.async_publish(self.hass, self._power_off_cmd_topic, payload)
        # Optimistically update the state
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._serial)},
            "name": f"Terneo {self._serial}",
            "manufacturer": "Terneo",
            "model": "AX",
        }