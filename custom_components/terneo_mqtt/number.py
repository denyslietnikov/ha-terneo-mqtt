"""Number platform for Terneo MQTT integration."""
import logging
from typing import Any

from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.components.number import NumberEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Terneo MQTT number entities."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.data.get("prefix", "terneo")

    entities = []
    for device in devices:
        client_id = device["client_id"]
        entities.append(TerneoNumber(client_id, prefix, "brightness", "Brightness", 0, 9, 1, "bright"))

    async_add_entities(entities)


class TerneoNumber(NumberEntity, RestoreEntity):
    """Representation of a Terneo number entity."""

    def __init__(
        self,
        client_id: str,
        prefix: str,
        sensor_type: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        topic_suffix: str,
    ) -> None:
        """Initialize the number entity."""
        self._client_id = client_id
        self._prefix = prefix
        self._sensor_type = sensor_type
        self._topic = f"{prefix}/{client_id}/{topic_suffix}"
        self._command_topic = f"{prefix}/{client_id}/{topic_suffix}"

        self._attr_name = f"Terneo {client_id} {name}"
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_value = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model="AX",  # Assuming AX, can be made configurable later
            name=f"Terneo {client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when entity is added."""
        await super().async_added_to_hass()
        
        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                try:
                    self._attr_native_value = float(last_state.state)
                    _LOGGER.debug("Restored %s state: %s", self._sensor_type, self._attr_native_value)
                except (ValueError, TypeError):
                    _LOGGER.warning("Could not restore %s state from %s", self._sensor_type, last_state.state)
        
        # Subscribe to MQTT topic
        self._unsubscribe = await mqtt.async_subscribe(self.hass, self._topic, self._handle_message, qos=0)
        
        # Publish current value to MQTT with retain if we have a value
        if self._attr_native_value is not None:
            payload = str(int(self._attr_native_value))
            await mqtt.async_publish(self.hass, self._topic, payload, qos=0, retain=True)
            _LOGGER.debug("Published restored %s value to MQTT: %s", self._sensor_type, payload)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topic when entity is removed."""
        if self._unsubscribe:
            self._unsubscribe()

    async def async_set_native_value(self, value: float) -> None:
        """Set the value of the entity."""
        payload = str(int(value))
        await mqtt.async_publish(self.hass, self._command_topic, payload, qos=0, retain=True)
        self._attr_native_value = value
        self.async_write_ha_state()

    @callback
    def _handle_message(self, msg: ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        _LOGGER.debug("Number %s received MQTT message: %s %s", self._sensor_type, msg.topic, msg.payload)
        try:
            self._attr_native_value = int(msg.payload)
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.warning("Invalid payload for %s: %s", self._sensor_type, msg.payload)