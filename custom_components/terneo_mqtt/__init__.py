"""Terneo MQTT integration for Home Assistant."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Terneo MQTT from a config entry."""
    # Forward the setup to the climate and sensor platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["climate", "sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["climate", "sensor"])