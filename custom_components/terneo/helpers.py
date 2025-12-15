"""Helper utilities for TerneoMQ integration."""

from homeassistant.config_entries import ConfigEntry


def get_mqtt_prefixes(config_entry: ConfigEntry) -> tuple[str, str]:
    """Return telemetry (publish) and command prefixes for MQTT."""
    publish_prefix = (
        config_entry.options.get("topic_prefix")
        or config_entry.options.get("publish_prefix")
        or config_entry.data.get("publish_prefix")
        or config_entry.data.get("prefix")
        or "terneo"
    )
    command_prefix = (
        config_entry.options.get("command_prefix")
        or config_entry.data.get("command_prefix")
        or publish_prefix
    )
    return publish_prefix, command_prefix
