"""Sensor platform for TerneoMQ integration."""

import time
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .base_entity import TerneoMQTTEntity
from .const import DOMAIN
from .coordinator import TerneoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TerneoMQ sensor platform."""
    devices = config_entry.data.get("devices", [])
    rated_power_w = config_entry.options.get(
        "rated_power_w", config_entry.data.get("rated_power_w", 0)
    )
    model = config_entry.options.get("model", config_entry.data.get("model", "AX"))
    entities = []
    for device in devices:
        client_id = device["client_id"]
        coordinator = hass.data[DOMAIN][config_entry.entry_id][client_id]
        entities.extend(
            [
                TerneoSensor(
                    hass=hass,
                    coordinator=coordinator,
                    sensor_type="floorTemp",
                    name="Floor Temperature",
                    device_class=SensorDeviceClass.TEMPERATURE,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="°C",
                    model=model,
                ),
                TerneoSensor(
                    hass=hass,
                    coordinator=coordinator,
                    sensor_type="protTemp",
                    name="Protection Temperature",
                    device_class=SensorDeviceClass.TEMPERATURE,
                    state_class=SensorStateClass.MEASUREMENT,
                    unit_of_measurement="°C",
                    model=model,
                ),
                TerneoStateSensor(
                    hass=hass,
                    coordinator=coordinator,
                    model=model,
                ),
            ]
        )
        # Add energy sensors if rated power is configured
        if rated_power_w > 0:
            entities.extend(
                [
                    TerneoPowerSensor(
                        hass=hass,
                        coordinator=coordinator,
                        rated_power_w=rated_power_w,
                        model=model,
                    ),
                    TerneoEnergySensor(
                        hass=hass,
                        coordinator=coordinator,
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
        hass: HomeAssistant,
        coordinator: TerneoCoordinator,
        sensor_type: str,
        name: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        unit_of_measurement: str | None,
        model: str = "AX",
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, sensor_type, name, sensor_type, model)
        self._attr_unique_id = f"{self._client_id}_{sensor_type}"
        self._attr_name = f"Terneo {self._client_id} {name}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_native_value = coordinator.get_value(sensor_type)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {self._client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when entity is added."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topic when entity is removed."""
        await super().async_will_remove_from_hass()

    def parse_value(self, payload: str) -> float | int:
        """Parse MQTT payload for sensor."""
        if self._sensor_type in ["floor_temp", "prot_temp"]:
            return float(payload)
        if self._sensor_type == "load":
            return int(payload)
        raise ValueError(f"Unknown sensor type {self._sensor_type}")

    def update_value(self, value: float) -> None:
        """Update sensor value."""
        self._attr_native_value = value


class TerneoStateSensor(SensorEntity):
    """Representation of a Terneo state sensor."""

    def __init__(
        self, hass: HomeAssistant, coordinator: TerneoCoordinator, model: str = "AX"
    ) -> None:
        """Initialize the mode sensor."""
        self.hass = hass
        self.coordinator = coordinator
        self._client_id = coordinator.client_id
        self._model = model
        self._attr_unique_id = f"{coordinator.client_id}_state"
        self._attr_name = f"Terneo {coordinator.client_id} State"
        self._attr_native_value = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {self._client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Listen to coordinator updates."""
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{DOMAIN}_{self._client_id}_update",
            self._handle_coordinator_update,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from dispatcher when entity is removed."""
        if self._unsub_dispatcher:
            self._unsub_dispatcher()

    @callback
    def _handle_coordinator_update(self, key: str, value: Any) -> None:
        """Handle update from coordinator."""
        if key in ["powerOff", "load", "mode"]:
            self._update_mode()
            self.async_write_ha_state()

    def _update_mode(self) -> None:
        """Update mode value based on powerOff, load and mode."""
        power_off = self.coordinator.get_value("powerOff")
        load = self.coordinator.get_value("load")
        if power_off == 1:
            self._attr_native_value = "Off"
        elif load == 1:
            self._attr_native_value = "Heat"
        else:
            self._attr_native_value = "Idle"


class TerneoPowerSensor(SensorEntity):
    """Representation of a Terneo power sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "W"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TerneoCoordinator,
        rated_power_w: int,
        model: str = "AX",
    ) -> None:
        """Initialize the power sensor."""
        self.hass = hass
        self.coordinator = coordinator
        self._client_id = coordinator.client_id
        self._rated_power_w = rated_power_w
        self._model = model
        self._model = model

        self._attr_unique_id = f"{self._client_id}_power"
        self._attr_name = f"Terneo {self._client_id} Power"
        self._attr_native_value = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {self._client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Listen to coordinator updates."""
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{DOMAIN}_{self._client_id}_update",
            self._handle_coordinator_update,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from dispatcher when entity is removed."""
        if self._unsub_dispatcher:
            self._unsub_dispatcher()

    @callback
    def _handle_coordinator_update(self, key: str, value: Any) -> None:
        """Handle update from coordinator."""
        if key == "load":
            self._attr_native_value = value * self._rated_power_w
            self.async_write_ha_state()


class TerneoEnergySensor(RestoreEntity, SensorEntity):
    """Representation of a Terneo energy sensor."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TerneoCoordinator,
        rated_power_w: int,
        model: str = "AX",
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__()
        self.hass = hass
        self.coordinator = coordinator
        self._client_id = coordinator.client_id
        self._rated_power_w = rated_power_w
        self._model = model
        self._load = None
        self._last_update = time.time()
        self._energy_kwh = 0.0

        self._attr_unique_id = f"{self._client_id}_energy"
        self._attr_name = f"Terneo {self._client_id} Energy"
        self._attr_native_value = 0.0

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {self._client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Set up restore and dispatcher listener."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._energy_kwh = float(last_state.state)
            except ValueError:
                self._energy_kwh = 0.0
        # Additional listener for load updates
        self._unsub_load_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{DOMAIN}_{self._client_id}_update",
            self._handle_load_update,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from dispatcher when entity is removed."""
        if self._unsub_load_dispatcher:
            self._unsub_load_dispatcher()
        await super().async_will_remove_from_hass()

    @callback
    def _handle_load_update(self, key: str, value: Any) -> None:
        """Handle load update from coordinator."""
        if key == "load":
            self._handle_load_change(value)

    def _handle_load_change(self, new_load: int) -> None:
        """Handle load change."""
        current_time = time.time()
        if self._load is not None:
            time_diff_hours = (current_time - self._last_update) / 3600.0
            power_kw = (self._load * self._rated_power_w) / 1000.0
            self._energy_kwh += power_kw * time_diff_hours
        self._load = new_load
        self._last_update = current_time
        self._attr_native_value = round(self._energy_kwh, 6)
        self.async_write_ha_state()
