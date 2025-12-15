"""TerneoMQ integration for Home Assistant."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import TerneoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TerneoMQ from a config entry."""
    # Create coordinators for each device
    hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    prefix = entry.options.get("topic_prefix", entry.data.get("prefix", "terneo"))
    for device in entry.data.get("devices", []):
        client_id = device["client_id"]
        coordinator = TerneoCoordinator(
            hass, client_id, prefix, True
        )  # supports_air_temp=True for now
        hass.data[DOMAIN][entry.entry_id][client_id] = coordinator
        await coordinator.async_setup()

    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, ["climate", "sensor", "binary_sensor", "number", "select"]
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Teardown coordinators
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        for coordinator in hass.data[DOMAIN][entry.entry_id].values():
            await coordinator.async_teardown()
        del hass.data[DOMAIN][entry.entry_id]

    return await hass.config_entries.async_unload_platforms(
        entry, ["climate", "sensor", "binary_sensor", "number", "select"]
    )
