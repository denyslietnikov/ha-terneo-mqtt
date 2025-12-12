"""Sensor platform for Terneo MQTT integration."""
import json
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

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base_entity import TerneoMQTTEntity
from .const import DOMAIN
from .http_coordinator import TerneoHTTPCoordinator


async def async_setup_entry(
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Terneo MQTT sensor platform."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.options.get("topic_prefix", config_entry.data.get("prefix", "terneo"))
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

    # Add HTTP telemetry sensors if coordinators exist
    coordinators = {}
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        coordinators = hass.data[DOMAIN][config_entry.entry_id].get("coordinators", {})
    http_entities = []
    for device in devices:
        client_id = device["client_id"]
        host = device.get("host")
        if host and host in coordinators:
            coordinator = coordinators[host]
            http_entities.extend([
                TerneoHTTPSensor(
                    coordinator=coordinator,
                    client_id=client_id,
                    sensor_type="wifi_rssi",
                    name="Wi-Fi RSSI",
                    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="dBm",
                    data_key="o.0",
                ),
                TerneoHTTPSensor(
                    coordinator=coordinator,
                    client_id=client_id,
                    sensor_type="reboot_reason",
                    name="Reboot Reason",
                    device_class=None,
                    state_class=None,
                    unit_of_measurement=None,
                    data_key="o.1",
                ),
                TerneoHTTPSensor(
                    coordinator=coordinator,
                    client_id=client_id,
                    sensor_type="power",
                    name="Power",
                    device_class=SensorDeviceClass.POWER,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="W",
                    data_key="p.0",
                ),
                TerneoHTTPSensor(
                    coordinator=coordinator,
                    client_id=client_id,
                    sensor_type="energy",
                    name="Energy",
                    device_class=SensorDeviceClass.ENERGY,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                    unit_of_measurement="Wh",
                    data_key="w.0",
                ),
                TerneoHTTPSensor(
                    coordinator=coordinator,
                    client_id=client_id,
                    sensor_type="current",
                    name="Current",
                    device_class=None,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="A",
                    data_key="i.0",
                ),
                TerneoHTTPSensor(
                    coordinator=coordinator,
                    client_id=client_id,
                    sensor_type="voltage",
                    name="Voltage",
                    device_class=SensorDeviceClass.VOLTAGE,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="V",
                    data_key="u.0",
                ),
                TerneoHTTPDiagnosticSensor(
                    coordinator=coordinator,
                    client_id=client_id,
                    sensor_type="http_telemetry",
                    name="HTTP Telemetry",
                    data_key=None,  # Full data
                ),
            ])
        if http_entities:
            async_add_entities(http_entities)


class TerneoSensor(TerneoMQTTEntity, SensorEntity):
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
        super().__init__(None, client_id, prefix, sensor_type, name, topic_suffix)  # hass will be set later
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_name = f"Terneo {client_id} {name}"
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

    def parse_value(self, payload: str) -> float | int:
        """Parse MQTT payload for sensor."""
        if self._sensor_type in ["floor_temp", "prot_temp"]:
            return float(payload)
        elif self._sensor_type == "load":
            return int(payload)
        else:
            raise ValueError(f"Unknown sensor type {self._sensor_type}")

    def update_value(self, value: float | int) -> None:
        """Update sensor value."""
        self._attr_native_value = value


class TerneoHTTPSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Terneo HTTP telemetry sensor."""

    def __init__(
        self,
        coordinator: TerneoHTTPCoordinator,
        client_id: str,
        sensor_type: str,
        name: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        unit_of_measurement: str | None,
        data_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._client_id = client_id
        self._sensor_type = sensor_type
        self._data_key = data_key
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_name = f"Terneo {client_id} {name}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_native_value = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model="AX",
            name=f"Terneo {client_id}",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if data and self._data_key in data:
            self._attr_native_value = data[self._data_key]
        else:
            self._attr_native_value = None
        self.async_write_ha_state()


class TerneoHTTPDiagnosticSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Terneo HTTP telemetry diagnostic sensor."""

    def __init__(
        self,
        coordinator: TerneoHTTPCoordinator,
        client_id: str,
        sensor_type: str,
        name: str,
        data_key: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._client_id = client_id
        self._sensor_type = sensor_type
        self._data_key = data_key
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_name = f"Terneo {client_id} {name}"
        self._attr_native_value = None
        self._attr_entity_registry_enabled_default = False  # Hidden by default

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model="AX",
            name=f"Terneo {client_id}",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if data:
            if self._data_key:
                self._attr_native_value = data.get(self._data_key)
            else:
                # Full telemetry data as JSON string
                self._attr_native_value = json.dumps(data, indent=2)
        else:
            self._attr_native_value = None
        self.async_write_ha_state()
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
        super().__init__(None, client_id, prefix, sensor_type, name, topic_suffix)  # hass will be set later
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_name = f"Terneo {client_id} {name}"
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

    def parse_value(self, payload: str) -> float | int:
        """Parse MQTT payload for sensor."""
        if self._sensor_type in ["floor_temp", "prot_temp"]:
            return float(payload)
        elif self._sensor_type == "load":
            return int(payload)
        else:
            raise ValueError(f"Unknown sensor type {self._sensor_type}")

    def update_value(self, value: float | int) -> None:
        """Update sensor value."""
        self._attr_native_value = value