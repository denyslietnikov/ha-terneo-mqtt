"""Binary sensor platform for TerneoMQ integration."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import TerneoMQTTEntity
from .const import DOMAIN
from .coordinator import TerneoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TerneoMQ binary sensor platform."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.options.get(
        "topic_prefix", config_entry.data.get("prefix", "terneo")
    )
    supports_air_temp = config_entry.options.get("supports_air_temp", True)
    model = config_entry.options.get("model", config_entry.data.get("model", "AX"))
    entities = []
    coordinators = {}
    for device in devices:
        client_id = device["client_id"]
        coordinator = TerneoCoordinator(hass, client_id, prefix, supports_air_temp)
        coordinators[client_id] = coordinator
        await coordinator.async_setup()
        entities.append(
            TerneoBinarySensor(
                hass=hass,
                coordinator=coordinator,
                sensor_type="heating",
                name="Heating",
                device_class=BinarySensorDeviceClass.HEAT,
                model=model,
                topic_suffix="load",
            )
        )
    async_add_entities(entities)


class TerneoBinarySensor(TerneoMQTTEntity, BinarySensorEntity):
    """Representation of a Terneo binary sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TerneoCoordinator,
        sensor_type: str,
        name: str,
        device_class: BinarySensorDeviceClass | None,
        model: str = "AX",
        topic_suffix: str = "load",
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(hass, coordinator, sensor_type, name, topic_suffix, model)
        self._attr_device_class = device_class
        self._attr_is_on = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {coordinator.client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Listen to coordinator updates."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when entity is removed."""
        await super().async_will_remove_from_hass()

    def parse_value(self, payload: str) -> int:
        """Parse MQTT payload for binary sensor."""
        return int(payload)

    def update_value(self, value: int) -> None:
        """Update binary sensor value."""
        self._attr_is_on = value > 0
