"""Base entity for TerneoMQ integration."""
import logging
import time
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TerneoMQTTEntity(RestoreEntity, ABC):
    """Base class for TerneoMQ entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client_id: str,
        prefix: str,
        sensor_type: str,
        name: str,
        topic_suffix: str,
        track_availability: bool = True,
    ) -> None:
        """Initialize the base entity."""
        super().__init__()
        self.hass = hass
        self._client_id = client_id
        self._prefix = prefix
        self._sensor_type = sensor_type
        self._topic = f"{prefix}/{client_id}/{topic_suffix}"
        self._command_topic = f"{prefix}/{client_id}/{topic_suffix}"
        self._name = f"Terneo {client_id} {name}"
        self._unique_id = f"{client_id}_{sensor_type}"
        self._last_update = None
        self._attr_available = True  # Always available for settings
        self._unavailable_timer = None
        self.track_availability = track_availability

    @abstractmethod
    def parse_value(self, payload: str) -> Any:
        """Parse MQTT payload into entity value."""
        pass

    @abstractmethod
    def update_value(self, value: Any) -> None:
        """Update entity state with parsed value."""
        pass

    async def publish_command(self, payload: str) -> None:
        """Publish a command to MQTT."""
        _LOGGER.debug("Publishing %s command: %s to %s", self._sensor_type, payload, self._command_topic)
        await mqtt.async_publish(self.hass, self._command_topic, payload, qos=0, retain=True)

    async def async_added_to_hass(self) -> None:
        """Set up availability timer when entity is added."""
        await super().async_added_to_hass()
        if self.track_availability:
            self._unavailable_timer = async_track_time_interval(self.hass, self._check_availability, timedelta(minutes=5))

    async def async_will_remove_from_hass(self) -> None:
        """Cancel availability timer when entity is removed."""
        if self._unavailable_timer:
            self._unavailable_timer()
        await super().async_will_remove_from_hass()

    @callback
    def _check_availability(self, now=None) -> None:
        """Check if entity should be marked unavailable."""
        if self._last_update is None or time.time() - self._last_update > 300:
            if self.track_availability:
                self._attr_available = False
                self.async_write_ha_state()

    @callback
    def _handle_message(self, msg: ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        _LOGGER.debug("Received MQTT message for %s: %s %s", self._sensor_type, msg.topic, msg.payload)
        self._last_update = time.time()
        if self.track_availability:
            self._attr_available = True
        try:
            value = self.parse_value(msg.payload)
            self.update_value(value)
            self.async_write_ha_state()
        except (ValueError, TypeError) as e:
            _LOGGER.warning("Invalid payload for %s: %s (%s)", self._sensor_type, msg.payload, e)