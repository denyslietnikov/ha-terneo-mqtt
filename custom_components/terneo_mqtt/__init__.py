"""Terneo MQTT integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .http_coordinator import TerneoHTTPCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Terneo MQTT from a config entry."""
    devices = entry.data.get("devices", [])
    
    # Collect unique hosts with their sn
    host_configs = {}
    for device in devices:
        host = device.get("host")
        sn = device.get("sn")
        if host:
            if host not in host_configs:
                host_configs[host] = sn  # Use the sn from the first device with this host
    
    # Create coordinators for each unique host
    coordinators = {}
    for host, sn in host_configs.items():
        coordinator = TerneoHTTPCoordinator(hass, host, sn, 60)  # poll_interval from options? but per device?
        await coordinator.async_config_entry_first_refresh()
        coordinators[host] = coordinator
    
    if coordinators:
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinators": coordinators}

    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["climate", "sensor", "binary_sensor", "number", "select"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Close HTTP coordinators if exist
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        coordinators = hass.data[DOMAIN][entry.entry_id].get("coordinators", {})
        for coordinator in coordinators.values():
            await coordinator.async_close()

    return await hass.config_entries.async_unload_platforms(entry, ["climate", "sensor", "binary_sensor", "number", "select"])