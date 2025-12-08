"""Binary sensor platform for Terneo MQTT integration."""
import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Terneo MQTT binary sensor platform."""
    config = config_entry.data
    client_ids = config["client_ids"].split(",")
    prefix = config.get("topic_prefix", "terneo")
    entities = []
    for client_id in client_ids:
        client_id = client_id.strip()
        if client_id:
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


class TerneoBinarySensor(BinarySensorEntity):
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
        self._client_id = client_id
        self._prefix = prefix
        self._sensor_type = sensor_type
        self._topic = f"{prefix}/{client_id}/{topic_suffix}"
        self._attr_name = f"Terneo {client_id} {name}"
        self._attr_unique_id = f"{client_id}_{sensor_type}"
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
        await mqtt.async_subscribe(self.hass, self._topic, self._handle_message, qos=0)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topic when entity is removed."""
        await mqtt.async_unsubscribe(self.hass, self._topic)

    @callback
    def _handle_message(self, msg: ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        _LOGGER.debug("Binary sensor %s received MQTT message: %s %s", self._sensor_type, msg.topic, msg.payload)
        try:
            load = int(msg.payload)
            self._attr_is_on = load > 0
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid payload for binary sensor %s: %s", self._sensor_type, msg.payload)