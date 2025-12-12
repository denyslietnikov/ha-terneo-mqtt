"""Terneo MQTT integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .http_coordinator import TerneoHTTPCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Terneo MQTT from a config entry."""
    # Check if HTTP enrichment is enabled
    http_enabled = entry.options.get("http_enabled", False)
    if http_enabled:
        host = entry.options.get("host")
        sn = entry.options.get("sn") or None
        poll_interval = entry.options.get("poll_interval", 60)
        if host:
            coordinator = TerneoHTTPCoordinator(hass, host, sn, poll_interval)
            await coordinator.async_config_entry_first_refresh()
            hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator}
        else:
            _LOGGER.warning("HTTP enrichment enabled but no host specified")

    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["climate", "sensor", "binary_sensor", "number", "select"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Close HTTP coordinator if exists
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coordinator:
            await coordinator.async_close()

    return await hass.config_entries.async_unload_platforms(entry, ["climate", "sensor", "binary_sensor", "number", "select"])