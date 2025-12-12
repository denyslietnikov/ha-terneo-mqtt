"""Config flow for Terneo MQTT integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

class TerneoMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Terneo MQTT."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._devices = []
        self._device_configs = {}
        self._current_device_index = 0

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self.init_data = user_input
            self._devices = [cid.strip() for cid in user_input["client_ids"].split(",") if cid.strip()]
            if not self._devices:
                return self.async_abort(reason="no_devices")
            self._device_configs = {}
            self._current_device_index = 0
            return await self.async_step_device_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("client_ids", description="Comma-separated list of MQTT Client IDs (e.g., terneo_ax_1B0026,terneo_ax_058009)"): str,
                vol.Optional("topic_prefix", default="terneo", description="MQTT topic prefix used by the devices"): str,
            }),
        )

    async def async_step_device_config(self, user_input=None) -> FlowResult:
        """Handle device-specific configuration."""
        if self._current_device_index >= len(self._devices):
            # All devices configured, create entry
            devices = [
                {"client_id": cid, **self._device_configs.get(cid, {"host": "", "sn": ""})}
                for cid in self._devices
            ]
            data = {
                "prefix": self.init_data.get("topic_prefix", "terneo"),
                "devices": devices,
            }
            return self.async_create_entry(title="Terneo MQTT", data=data)

        client_id = self._devices[self._current_device_index]

        if user_input is not None:
            self._device_configs[client_id] = {
                "host": user_input.get("host", ""),
                "sn": user_input.get("sn", ""),
            }
            self._current_device_index += 1
            return await self.async_step_device_config()

        return self.async_show_form(
            step_id="device_config",
            data_schema=vol.Schema({
                vol.Optional("host", default="", description=f"Host/IP for {client_id} (optional)"): str,
                vol.Optional("sn", default="", description=f"Serial number for {client_id} (optional)"): str,
            }),
            description_placeholders={"device": client_id},
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
                vol.Optional(
                    "http_enabled",
                    default=self._config_entry.options.get("http_enabled", False)
                ): bool,
                vol.Optional(
                    "host",
                    default=self._config_entry.options.get("host", "")
                ): str,
                vol.Optional(
                    "sn",
                    default=self._config_entry.options.get("sn", "")
                ): str,
                vol.Optional(
                    "poll_interval",
                    default=self._config_entry.options.get("poll_interval", 60)
                ): int,
            }),
        )