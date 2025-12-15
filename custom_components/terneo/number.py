"""Number platform for TerneoMQ integration."""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import TerneoMQTTEntity
from .const import DOMAIN
from .coordinator import TerneoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TerneoMQ number entities."""
    devices = config_entry.data.get("devices", [])
    prefix = config_entry.options.get(
        "topic_prefix", config_entry.data.get("prefix", "terneo")
    )
    model = config_entry.options.get("model", config_entry.data.get("model", "AX"))

    entities = []
    coordinators = {}
    for device in devices:
        client_id = device["client_id"]
        coordinator = TerneoCoordinator(
            hass, client_id, prefix, True
        )  # supports_air_temp not used for number
        coordinators[client_id] = coordinator
        await coordinator.async_setup()
        entities.append(
            TerneoNumber(
                hass, coordinator, "brightness", "Brightness", 0, 9, 1, "bright", model
            )
        )

    async_add_entities(entities)


class TerneoNumber(TerneoMQTTEntity, NumberEntity):
    """Representation of a Terneo number entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TerneoCoordinator,
        sensor_type: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        topic_suffix: str,
        model: str = "AX",
    ) -> None:
        """Initialize the number entity."""
        super().__init__(
            hass,
            coordinator,
            sensor_type,
            name,
            topic_suffix,
            model,
            track_availability=False,
        )
        self._topic_suffix = topic_suffix
        self._topic = f"{coordinator.prefix}/{coordinator.client_id}/{topic_suffix}"
        self._command_topic = self._topic
        self._attr_unique_id = f"{coordinator.client_id}_{sensor_type}"
        self._attr_name = f"Terneo {coordinator.client_id} {name}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_value = coordinator.get_value(sensor_type)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {coordinator.client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Set up entity when added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                try:
                    self._attr_native_value = float(last_state.state)
                    _LOGGER.debug(
                        "Restored %s state: %s",
                        self._sensor_type,
                        self._attr_native_value,
                    )
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Could not restore %s state from %s",
                        self._sensor_type,
                        last_state.state,
                    )

    async def async_set_native_value(self, value: float) -> None:
        """Set the value of the entity."""
        payload = str(int(value))
        await self.publish_command(self._topic_suffix, payload)
        self._attr_native_value = value
        self.async_write_ha_state()

    def parse_value(self, payload: str) -> int:
        """Parse MQTT payload for number."""
        return int(payload)

    def update_value(self, value: int) -> bool:
        """Update number value."""
        self._attr_native_value = value
        return True
