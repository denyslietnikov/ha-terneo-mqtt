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
            return self.async_create_entry(title="Terneo MQTT", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("client_ids", description="Comma-separated list of MQTT Client IDs (e.g., terneo_ax_1B0026,terneo_ax_058009)"): str,
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
                    default=self.config_entry.options.get("topic_prefix", "terneo")
                ): str,
            }),
        )