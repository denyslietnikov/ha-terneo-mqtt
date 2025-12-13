"""Select platform for TerneoMQ integration."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import TerneoMQTTEntity
from .const import DOMAIN

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

    entities = []
    for device in devices:
        client_id = device["client_id"]
        entities.append(
            TerneoSelect(
                client_id,
                prefix,
                "mode",
                "Mode",
                ["schedule", "manual", "away", "temporary"],
                "mode",
            )
        )

    async_add_entities(entities)


class TerneoSelect(TerneoMQTTEntity, SelectEntity):
    """Representation of a Terneo select entity."""

    def __init__(
        self,
        client_id: str,
        prefix: str,
        sensor_type: str,
        name: str,
        options: list[str],
        topic_suffix: str,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(
            None,
            client_id,
            prefix,
            sensor_type,
            name,
            topic_suffix,
            track_availability=False,
        )  # hass will be set later
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_name = f"Terneo {client_id} {name}"
        self._options = options
        self._attr_options = options
        self._attr_current_option = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            manufacturer="Terneo",
            model="AX",  # Assuming AX, can be made configurable later
            name=f"Terneo {client_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when entity is added."""
        await super().async_added_to_hass()
        self.hass = self.hass  # Ensure hass is set

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self._options:
                self._attr_current_option = last_state.state
                _LOGGER.debug(
                    "Restored %s state: %s",
                    self._sensor_type,
                    self._attr_current_option,
                )

        # Subscribe to MQTT topic
        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self._topic, self._handle_message, qos=0
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topic when entity is removed."""
        if self._unsubscribe:
            self._unsubscribe()

    async def async_select_option(self, option: str) -> None:
        """Set the option of the entity."""
        # Map option to payload: schedule -> 0, manual -> 3, away -> 4, temporary -> 5
        payload_map = {"schedule": "0", "manual": "3", "away": "4", "temporary": "5"}
        payload = payload_map.get(option, "0")
        await self.publish_command(payload)
        self._attr_current_option = option
        self.async_write_ha_state()

    def parse_value(self, payload: str) -> str:
        """Parse MQTT payload for select."""
        value_map = {"0": "schedule", "3": "manual", "4": "away", "5": "temporary"}
        return value_map.get(payload, "schedule")

    def update_value(self, value: str) -> None:
        """Update select value."""
        if value in self._options:
            self._attr_current_option = value
        else:
            _LOGGER.warning("Unknown option for %s: %s", self._sensor_type, value)
