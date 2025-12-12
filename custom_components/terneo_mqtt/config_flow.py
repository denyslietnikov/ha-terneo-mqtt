"""Config flow for Terneo MQTT integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

class TerneoMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Terneo MQTT."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Parse devices_config into devices list
            devices_config = user_input["devices_config"]
            devices = []
            for dc in devices_config.split(","):
                parts = dc.strip().split(":")
                if len(parts) >= 1:
                    client_id = parts[0].strip()
                    host = parts[1].strip() if len(parts) > 1 else ""
                    sn = parts[2].strip() if len(parts) > 2 else ""
                    devices.append({"client_id": client_id, "host": host, "sn": sn})
            data = {
                "prefix": user_input.get("topic_prefix", "terneo"),
                "devices": devices,
            }
            return self.async_create_entry(title="Terneo MQTT", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("devices_config", description="Comma-separated device configs: client_id:host:sn (sn optional, e.g., terneo_ax_1:192.168.1.10:12345,terneo_ax_2:192.168.1.11)"): str,
                vol.Optional("topic_prefix", default="terneo", description="MQTT topic prefix used by the devices"): str,
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TerneoMQTTOptionsFlow(config_entry)


class TerneoMQTTOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Terneo MQTT."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "topic_prefix",
                    default=self._config_entry.options.get("topic_prefix", "terneo")
                ): str,
            }),
        )