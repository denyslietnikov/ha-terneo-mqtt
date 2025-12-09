"""Sensor platform for Terneo MQTT integration."""
import logging
from typing import Any

from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Terneo MQTT sensor platform."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.data.get("prefix", "terneo")
    entities = []
    for device in devices:
        client_id = device["client_id"]
        entities.extend([
                TerneoSensor(
                    client_id=client_id,
                    prefix=prefix,
                    sensor_type="floor_temp",
                    name="Floor Temperature",
                    device_class=SensorDeviceClass.TEMPERATURE,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="°C",
                    topic_suffix="floorTemp",
                ),
                TerneoSensor(
                    client_id=client_id,
                    prefix=prefix,
                    sensor_type="prot_temp",
                    name="Protection Temperature",
                    device_class=SensorDeviceClass.TEMPERATURE,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="°C",
                    topic_suffix="protTemp",
                ),
                TerneoSensor(
                    client_id=client_id,
                    prefix=prefix,
                    sensor_type="load",
                    name="Load",
                    device_class=None,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement=None,
                    topic_suffix="load",
                ),
            ])
    if entities:
        async_add_entities(entities)


class TerneoSensor(SensorEntity):
    """Representation of a Terneo sensor."""

    def __init__(
        self,
        client_id: str,
        prefix: str,
        sensor_type: str,
        name: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        unit_of_measurement: str | None,
        topic_suffix: str,
    ) -> None:
        """Initialize the sensor."""
        self._client_id = client_id
        self._prefix = prefix
        self._sensor_type = sensor_type
        self._topic = f"{prefix}/{client_id}/{topic_suffix}"
        self._attr_name = f"Terneo {client_id} {name}"
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_native_value = None

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

    @callback
    def _handle_message(self, msg: ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        _LOGGER.debug("Sensor %s received MQTT message: %s %s", self._sensor_type, msg.topic, msg.payload)
        try:
            if self._sensor_type in ["floor_temp", "prot_temp"]:
                self._attr_native_value = float(msg.payload)
            elif self._sensor_type == "load":
                self._attr_native_value = int(msg.payload)
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid payload for sensor %s: %s", self._sensor_type, msg.payload)