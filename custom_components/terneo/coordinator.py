"""Coordinator for Terneo MQTT integration."""

from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN


class TerneoCoordinator:
    """Coordinator for Terneo device MQTT communication."""

    def __init__(
        self,
        hass: HomeAssistant,
        client_id: str,
        telemetry_prefix: str,
        command_prefix: str,
        supports_air_temp: bool = True,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.client_id = client_id
        self.telemetry_prefix = telemetry_prefix
        self.command_prefix = command_prefix
        self.supports_air_temp = supports_air_temp
        self._data: dict[str, Any] = {}
        self._subscriptions: list[Any] = []

    async def async_setup(self) -> None:
        """Set up MQTT subscriptions."""
        topics = [
            (
                "floorTemp",
                f"{self.telemetry_prefix}/{self.client_id}/floorTemp",
            ),
            (
                "protTemp",
                f"{self.telemetry_prefix}/{self.client_id}/protTemp",
            ),
            ("setTemp", f"{self.telemetry_prefix}/{self.client_id}/setTemp"),
            ("load", f"{self.telemetry_prefix}/{self.client_id}/load"),
            ("powerOff", f"{self.telemetry_prefix}/{self.client_id}/powerOff"),
            ("mode", f"{self.telemetry_prefix}/{self.client_id}/mode"),
            ("bright", f"{self.telemetry_prefix}/{self.client_id}/bright"),
        ]
        if self.supports_air_temp:
            topics.append(
                ("airTemp", f"{self.telemetry_prefix}/{self.client_id}/airTemp")
            )
        if self.command_prefix != self.telemetry_prefix:
            topics.append(
                ("powerOff", f"{self.command_prefix}/{self.client_id}/powerOff")
            )

        for key, topic in topics:
            unsub = await mqtt.async_subscribe(
                self.hass, topic, self._handle_message, qos=0
            )
            self._subscriptions.append(unsub)

    async def async_teardown(self) -> None:
        """Unsubscribe from MQTT topics."""
        for unsub in self._subscriptions:
            unsub()
        self._subscriptions.clear()

    @callback
    def _handle_message(self, msg: ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        topic_parts = msg.topic.split("/")
        if len(topic_parts) >= 3:
            key = topic_parts[-1]  # e.g., floorTemp
            try:
                payload_str = (
                    msg.payload.decode()
                    if isinstance(msg.payload, bytes)
                    else str(msg.payload)
                )
                if key in ["load", "powerOff", "mode", "bright"]:
                    value = int(payload_str)
                elif key in ["floorTemp", "airTemp", "protTemp", "setTemp"]:
                    value = float(payload_str)
                else:
                    value = payload_str
                self._data[key] = value
                # Send update signal
                async_dispatcher_send(
                    self.hass,
                    f"{DOMAIN}_{self.client_id}_update",
                    key,
                    value,
                )
            except (ValueError, AttributeError):
                pass

    def get_value(self, key: str) -> Any:
        """Get current value for a key."""
        return self._data.get(key)

    def set_cached_value(self, key: str, value: Any) -> None:
        """Cache a value locally without waiting for telemetry."""
        self._data[key] = value

    async def publish_command(
        self, topic_suffix: str, payload: str, retain: bool = False
    ) -> None:
        """Publish a command to MQTT."""
        topic = f"{self.command_prefix}/{self.client_id}/{topic_suffix}"
        await mqtt.async_publish(self.hass, topic, payload, retain=retain)
