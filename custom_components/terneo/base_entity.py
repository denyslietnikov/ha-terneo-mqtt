"""Base entity for TerneoMQ integration."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any

from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import TerneoCoordinator

_LOGGER = logging.getLogger(__name__)


class TerneoMQTTEntity(RestoreEntity, ABC):
    """Base class for TerneoMQ entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: "TerneoCoordinator",
        sensor_type: str,
        name: str,
        topic_suffix: str,
        model: str = "AX",
        track_availability: bool = True,
    ) -> None:
        """Initialize the base entity."""
        super().__init__()
        self.hass = hass
        self.coordinator = coordinator
        self._client_id = coordinator.client_id
        self._sensor_type = sensor_type
        self._topic_suffix = topic_suffix
        self._name = f"Terneo {coordinator.client_id} {name}"
        self._unique_id = f"{self._client_id}_{sensor_type}"
        self._attr_unique_id = self._unique_id
        self._attr_name = self._name
        self._last_update = None
        self._attr_available = True  # Always available for settings
        self._unavailable_timer = None
        self.track_availability = track_availability
        self._model = model
        self._topic = f"{coordinator.prefix}/{coordinator.client_id}/{topic_suffix}"
        self._unsubscribe = None

    @abstractmethod
    def parse_value(self, payload: str) -> Any:
        """Parse MQTT payload into entity value."""

    @abstractmethod
    def update_value(self, value: Any) -> None:
        """Update entity state with parsed value."""

    async def publish_command(self, topic_suffix: str, payload: str) -> None:
        """Publish a command to MQTT."""
        _LOGGER.debug(
            "Publishing %s command: %s to %s",
            self._sensor_type,
            payload,
            topic_suffix,
        )
        await self.coordinator.publish_command(topic_suffix, payload)

    async def async_added_to_hass(self) -> None:
        """Set up availability timer and dispatcher listener when entity is added."""
        await super().async_added_to_hass()
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{DOMAIN}_{self._client_id}_update",
            self._handle_coordinator_update,
        )
        if self.track_availability:
            self._unavailable_timer = async_track_time_interval(
                self.hass, self._check_availability, timedelta(minutes=5)
            )

    async def async_will_remove_from_hass(self) -> None:
        """Cancel availability timer and dispatcher listener when entity is removed."""
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
        if self._unavailable_timer:
            self._unavailable_timer()
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self, key: str, value: Any) -> None:
        """Handle update from coordinator."""
        if key == self._topic_suffix:
            self.update_value(value)
            self._last_update = time.time()
            self._attr_available = True
            self.async_write_ha_state()

    @callback
    def _check_availability(self, now: Any) -> None:
        """Check if entity is still available based on last update time."""
        if self._last_update and (time.time() - self._last_update) > 300:  # 5 minutes
            self._attr_available = False
            self.async_write_ha_state()

    @callback
    def _handle_message(self, msg: ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        _LOGGER.debug(
            "Received MQTT message for %s: %s %s",
            self._sensor_type,
            msg.topic,
            msg.payload,
        )
        self._last_update = time.time()
        if self.track_availability:
            self._attr_available = True
        try:
            value = self.parse_value(msg.payload)
            self.update_value(value)
            self.async_write_ha_state()
        except (ValueError, TypeError) as e:
            _LOGGER.warning(
                "Invalid payload for %s: %s (%s)", self._sensor_type, msg.payload, e
            )
