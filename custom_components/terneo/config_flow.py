"""Config flow for TerneoMQ integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class TerneoMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TerneoMQ."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            devices = [
                cid.strip()
                for cid in user_input["client_ids"].split(",")
                if cid.strip()
            ]
            if not devices:
                return self.async_abort(reason="no_devices")

            publish_prefix = user_input.get("topic_prefix", "terneo")
            command_prefix = user_input.get("command_prefix", publish_prefix)
            data = {
                "prefix": publish_prefix,
                "publish_prefix": publish_prefix,
                "command_prefix": command_prefix,
                "model": user_input.get("model", "AX"),
                "rated_power_w": user_input.get("rated_power_w", 0),
                "devices": [{"client_id": cid} for cid in devices],
            }
            return self.async_create_entry(title="TerneoMQ", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "client_ids",
                        description="Comma-separated list of MQTT Client IDs (e.g., terneo_ax_1B0026,terneo_ax_058009)",
                    ): str,
                    vol.Optional(
                        "topic_prefix",
                        default="terneo",
                        description="MQTT topic prefix used by the devices (publish)",
                    ): str,
                    vol.Optional(
                        "command_prefix",
                        default="terneo",
                        description="MQTT topic prefix for command subscriptions",
                    ): str,
                    vol.Optional(
                        "model",
                        default="AX",
                        description="Thermostat model",
                    ): vol.In({"AX": "AX", "SX": "SX"}),
                    vol.Optional(
                        "rated_power_w",
                        default=0,
                        description="Rated power of heating element in watts (0 = disabled)",
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=10000)),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TerneoMQTTOptionsFlow(config_entry)


class TerneoMQTTOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for TerneoMQ."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Reload integration to apply new options
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "topic_prefix",
                        default=self._config_entry.options.get(
                            "topic_prefix",
                            self._config_entry.data.get(
                                "publish_prefix",
                                self._config_entry.data.get("prefix", "terneo"),
                            ),
                        ),
                    ): str,
                    vol.Optional(
                        "command_prefix",
                        default=self._config_entry.options.get(
                            "command_prefix",
                            self._config_entry.data.get(
                                "command_prefix",
                                self._config_entry.data.get(
                                    "publish_prefix",
                                    self._config_entry.data.get("prefix", "terneo"),
                                ),
                            ),
                        ),
                        description="MQTT topic prefix for command subscriptions",
                    ): str,
                    vol.Optional(
                        "supports_air_temp",
                        default=self._config_entry.options.get(
                            "supports_air_temp", True
                        ),
                        description="Whether devices support air temperature sensor",
                    ): bool,
                    vol.Optional(
                        "model",
                        default=self._config_entry.options.get("model", "AX"),
                        description="Thermostat model",
                    ): vol.In({"AX": "AX", "SX": "SX"}),
                    vol.Optional(
                        "rated_power_w",
                        default=self._config_entry.options.get("rated_power_w", 0),
                        description="Rated power of heating element in watts (0 = disabled)",
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=10000)),
                }
            ),
        )
