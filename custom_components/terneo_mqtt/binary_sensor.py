"""Binary sensor platform for TerneoMQ integration."""
import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import TerneoMQTTEntity
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TerneoMQ binary sensor platform."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.options.get("topic_prefix", config_entry.data.get("prefix", "terneo"))
    entities = []
    for device in devices:
        client_id = device["client_id"]
        entities.append(
            TerneoBinarySensor(
                client_id=client_id,
                prefix=prefix,
                sensor_type="heating",
                    name="Heating",
                    device_class=BinarySensorDeviceClass.HEAT,
                    topic_suffix="load",
                )
            )
    if entities:
        async_add_entities(entities)


class TerneoBinarySensor(TerneoMQTTEntity, BinarySensorEntity):
    """Representation of a Terneo binary sensor."""

    def __init__(
        self,
        client_id: str,
        prefix: str,
        sensor_type: str,
        name: str,
        device_class: BinarySensorDeviceClass | None,
        topic_suffix: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(None, client_id, prefix, sensor_type, name, topic_suffix)  # hass will be set later
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_name = f"Terneo {client_id} {name}"
        self._attr_device_class = device_class
        self._attr_is_on = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model="AX",  # Assuming AX, can be made configurable later
            name=f"Terneo {client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when entity is added."""
        self._unsubscribe = await mqtt.async_subscribe(self.hass, self._topic, self._handle_message, qos=0)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topic when entity is removed."""
        if self._unsubscribe:
            self._unsubscribe()

    def parse_value(self, payload: str) -> int:
        """Parse MQTT payload for binary sensor."""
        return int(payload)

    def update_value(self, value: int) -> None:
        """Update binary sensor value."""
        self._attr_is_on = value > 0