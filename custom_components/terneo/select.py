"""Select platform for TerneoMQ integration."""

import logging

from homeassistant.components.select import SelectEntity
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
    """Set up the TerneoMQ select entities."""
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
        )  # supports_air_temp not used for select
        coordinators[client_id] = coordinator
        await coordinator.async_setup()
        entities.append(
            TerneoSelect(
                hass,
                coordinator,
                "mode",
                "Mode",
                ["schedule", "manual", "away", "temporary"],
                "mode",
                model,
            )
        )

    async_add_entities(entities)


class TerneoSelect(TerneoMQTTEntity, SelectEntity):
    """Representation of a Terneo select entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TerneoCoordinator,
        sensor_type: str,
        name: str,
        options: list[str],
        topic_suffix: str,
        model: str = "AX",
    ) -> None:
        """Initialize the select entity."""
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
        self._attr_unique_id = f"{coordinator.client_id}_{sensor_type}"
        self._attr_name = f"Terneo {coordinator.client_id} {name}"
        self._options = options
        self._attr_options = options
        self._attr_current_option = self.parse_value(
            str(coordinator.get_value(sensor_type) or 0)
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.client_id)},
            manufacturer="Terneo",
            model=self._model,
            name=f"Terneo {coordinator.client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Set up entity when added to hass."""
        await super().async_added_to_hass()

    async def async_select_option(self, option: str) -> None:
        """Set the option of the entity."""
        # Map option to payload: schedule -> 0, manual -> 3, away -> 4, temporary -> 5
        payload_map = {"schedule": "0", "manual": "3", "away": "4", "temporary": "5"}
        payload = payload_map.get(option, "0")
        await self.publish_command(self._topic_suffix, payload)
        self._attr_current_option = option
        self.async_write_ha_state()

    def parse_value(self, payload: str) -> str:
        """Parse MQTT payload for select."""
        value_map = {"0": "schedule", "3": "manual", "4": "away", "5": "temporary"}
        return value_map.get(payload, "schedule")

    def update_value(self, value: str) -> None:
        """Update select value."""
        parsed_value = self.parse_value(value)
        if parsed_value in self._options:
            self._attr_current_option = parsed_value
        else:
            _LOGGER.warning("Unknown option for %s: %s", self._sensor_type, value)
