"""TerneoMQ integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TerneoMQ from a config entry."""
    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, ["climate", "sensor", "binary_sensor", "number", "select"]
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry, ["climate", "sensor", "binary_sensor", "number", "select"]
    )
