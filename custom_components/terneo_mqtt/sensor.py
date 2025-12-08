"""Sensor platform for Terneo MQTT integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import mqtt, sensor
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Terneo MQTT sensor from a config entry."""
    serial = config_entry.data.get("serial")
    topic_prefix = config_entry.options.get("topic_prefix", config_entry.data.get("topic_prefix", "terneo"))
    if serial:
        async_add_entities([TerneoMQTTSensor(hass, serial, topic_prefix, "floorTemp", "Floor Temperature")])


class TerneoMQTTSensor(SensorEntity):
    """Representation of a Terneo MQTT sensor."""

    _attr_device_class = sensor.SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_state_class = sensor.SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, serial: str, topic_prefix: str, sensor_type: str, name: str) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._serial = serial
        self._topic_prefix = topic_prefix
        self._sensor_type = sensor_type
        self._topic = f"{topic_prefix}/{serial}/{sensor_type}"
        self._attr_unique_id = f"terneo_{serial}_{sensor_type}"
        self._attr_name = f"Terneo {serial} {name}"
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics."""
        self._unsub = await mqtt.async_subscribe(
            self.hass, self._topic, self._handle_message, 0
        )
        self.async_on_remove(self._unsub)

    @callback
    def _handle_message(self, msg) -> None:
        """Handle status message from MQTT."""
        _LOGGER.debug("Received MQTT message: %s %s", msg.topic, msg.payload)
        try:
            self._attr_native_value = float(msg.payload.decode())
            self.async_write_ha_state()
        except (ValueError, UnicodeDecodeError):
            _LOGGER.error("Invalid payload in message: %s", msg.payload)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._serial)},
            "name": f"Terneo {self._serial}",
            "manufacturer": "Terneo",
            "model": "SX",
        }