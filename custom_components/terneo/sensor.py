"""Sensor platform for TerneoMQ integration."""

import time

from homeassistant.components import mqtt
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE

from .base_entity import TerneoMQTTEntity
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TerneoMQ sensor platform."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.options.get(
        "topic_prefix", config_entry.data.get("prefix", "terneo")
    )
    rated_power_w = config_entry.options.get(
        "rated_power_w", config_entry.data.get("rated_power_w", 0)
    )
    model = config_entry.options.get("model", config_entry.data.get("model", "AX"))
    entities = []
    for device in devices:
        client_id = device["client_id"]
        entities.extend(
            [
                TerneoSensor(
                    client_id=client_id,
                    prefix=prefix,
                    sensor_type="floor_temp",
                    name="Floor Temperature",
                    device_class=SensorDeviceClass.TEMPERATURE,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="°C",
                    topic_suffix="floorTemp",
                    model=model,
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
                    model=model,
                ),
                TerneoStateSensor(
                    client_id=client_id,
                    prefix=prefix,
                    model=model,
                ),
            ]
        )
        # Add energy sensors if rated power is configured
        if rated_power_w > 0:
            entities.extend(
                [
                    TerneoPowerSensor(
                        client_id=client_id,
                        prefix=prefix,
                        rated_power_w=rated_power_w,
                        model=model,
                    ),
                    TerneoEnergySensor(
                        client_id=client_id,
                        prefix=prefix,
                        rated_power_w=rated_power_w,
                        model=model,
                    ),
                ]
            )
    if entities:
        async_add_entities(entities)


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
        model: str = "AX",
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            None, client_id, prefix, sensor_type, name, topic_suffix, model
        )  # hass will be set later
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_name = f"Terneo {client_id} {name}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_native_value = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when entity is added."""
        await super().async_added_to_hass()
        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self._topic, self._handle_message, qos=0
        )

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


class TerneoStateSensor(SensorEntity):
    """Representation of a Terneo state sensor."""

    def __init__(self, client_id: str, prefix: str, model: str = "AX") -> None:
        """Initialize the mode sensor."""
        self._client_id = client_id
        self._prefix = prefix
        self._model = model
        self._attr_unique_id = f"{client_id}_state"
        self._attr_name = f"Terneo {client_id} State"
        self._attr_native_value = None
        self._power_off = None
        self._load = None
        self._mode = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics when entity is added."""
        self._unsub_power_off = await mqtt.async_subscribe(
            self.hass,
            f"{self._prefix}/{self._client_id}/powerOff",
            self._handle_message,
            qos=0,
        )
        self._unsub_load = await mqtt.async_subscribe(
            self.hass,
            f"{self._prefix}/{self._client_id}/load",
            self._handle_message,
            qos=0,
        )
        self._unsub_mode = await mqtt.async_subscribe(
            self.hass,
            f"{self._prefix}/{self._client_id}/mode",
            self._handle_message,
            qos=0,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topics when entity is removed."""
        if hasattr(self, "_unsub_power_off"):
            self._unsub_power_off()
        if hasattr(self, "_unsub_load"):
            self._unsub_load()
        if hasattr(self, "_unsub_mode"):
            self._unsub_mode()

    @callback
    def _handle_message(self, msg) -> None:
        """Handle status message from MQTT."""
        try:
            updated = False
            if msg.topic.endswith("/powerOff"):
                self._power_off = int(msg.payload)
                updated = True
            elif msg.topic.endswith("/load"):
                self._load = int(msg.payload)
                updated = True
            elif msg.topic.endswith("/mode"):
                self._mode = int(msg.payload)
                updated = True

            if updated:
                self._update_mode()
                self.async_write_ha_state()
        except ValueError:
            pass

    def _update_mode(self) -> None:
        """Update mode value based on powerOff, load and mode."""
        if self._power_off == 1:
            self._attr_native_value = "Off"
        else:
            if self._load == 1:
                self._attr_native_value = "Heat"
            else:
                self._attr_native_value = "Idle"


class TerneoPowerSensor(SensorEntity):
    """Representation of a Terneo power sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "W"

    def __init__(
        self, client_id: str, prefix: str, rated_power_w: int, model: str = "AX"
    ) -> None:
        """Initialize the power sensor."""
        self._client_id = client_id
        self._topic_prefix = prefix
        self._rated_power_w = rated_power_w
        self._model = model
        self._load_topic = f"{prefix}/{client_id}/load"
        self._load = None

        self._attr_unique_id = f"{client_id}_power"
        self._attr_name = f"Terneo {client_id} Power"
        self._attr_native_value = None
        self.entity_id = f"sensor.terneo_{client_id}_power"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics when entity is added."""
        self._unsub_load = await mqtt.async_subscribe(
            self.hass, self._load_topic, self._handle_load_message, 0
        )
        self.async_on_remove(self._unsub_load)

    @callback
    def _handle_load_message(self, msg) -> None:
        """Handle load message from MQTT."""
        try:
            self._load = int(msg.payload)
            self._attr_native_value = self._load * self._rated_power_w
            self.async_write_ha_state()
        except ValueError:
            pass


class TerneoEnergySensor(RestoreEntity, SensorEntity):
    """Representation of a Terneo energy sensor."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    def __init__(
        self, client_id: str, prefix: str, rated_power_w: int, model: str = "AX"
    ) -> None:
        """Initialize the energy sensor."""
        self._client_id = client_id
        self._topic_prefix = prefix
        self._rated_power_w = rated_power_w
        self._model = model
        self._load_topic = f"{prefix}/{client_id}/load"
        self._load = None
        self._last_update = time.time()
        self._energy_kwh = 0.0

        self._attr_unique_id = f"{client_id}_energy"
        self._attr_name = f"Terneo {client_id} Energy"
        self._attr_native_value = 0.0
        self.entity_id = f"sensor.terneo_{client_id}_energy"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics when entity is added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._energy_kwh = float(last_state.state)
            except ValueError:
                self._energy_kwh = 0.0
        self._unsub_load = await mqtt.async_subscribe(
            self.hass, self._load_topic, self._handle_load_message, 0
        )
        self.async_on_remove(self._unsub_load)

    @callback
    def _handle_load_message(self, msg) -> None:
        """Handle load message from MQTT."""
        try:
            new_load = int(msg.payload)
            current_time = time.time()

            # Calculate energy consumed since last update
            if self._load is not None:
                time_diff_hours = (current_time - self._last_update) / 3600.0
                power_kw = (self._load * self._rated_power_w) / 1000.0
                self._energy_kwh += power_kw * time_diff_hours

            self._load = new_load
            self._last_update = current_time
            self._attr_native_value = round(self._energy_kwh, 6)
            self.async_write_ha_state()
        except ValueError:
            pass
