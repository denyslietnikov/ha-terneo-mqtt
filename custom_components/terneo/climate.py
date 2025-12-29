"""Climate platform for TerneoMQ integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components import climate
from homeassistant.components.climate import ClimateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import TerneoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TerneoMQ climate from a config entry."""
    devices = config_entry.data.get("devices", [])
    model = config_entry.options.get("model", config_entry.data.get("model", "AX"))
    entities = []
    for device in devices:
        client_id = device["client_id"]
        coordinator = hass.data[DOMAIN][config_entry.entry_id][client_id]
        entities.append(TerneoMQTTClimate(hass, coordinator, model))
    if entities:
        async_add_entities(entities)


class TerneoMQTTClimate(RestoreEntity, ClimateEntity):
    """Representation of a TerneoMQ climate device."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        climate.ClimateEntityFeature.TARGET_TEMPERATURE
        | climate.ClimateEntityFeature.TURN_OFF
        | climate.ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = [
        climate.HVACMode.HEAT,
        climate.HVACMode.OFF,
        climate.HVACMode.AUTO,
    ]
    _attr_hvac_mode = climate.HVACMode.OFF
    _attr_hvac_action = climate.HVACAction.OFF
    _attr_min_temp = 5
    _attr_max_temp = 35
    _attr_precision = 0.5

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TerneoCoordinator,
        model: str = "AX",
    ) -> None:
        """Initialize the climate device."""
        self.hass = hass
        self.coordinator = coordinator
        self._client_id = coordinator.client_id
        self._model = model
        self._supports_air_temp = coordinator.supports_air_temp
        # Status topics
        telemetry_prefix = coordinator.telemetry_prefix
        command_prefix = coordinator.command_prefix
        self._air_temp_topic = f"{telemetry_prefix}/{self._client_id}/airTemp"
        self._floor_temp_topic = f"{telemetry_prefix}/{self._client_id}/floorTemp"
        self._set_temp_topic = f"{telemetry_prefix}/{self._client_id}/setTemp"
        self._load_topic = f"{telemetry_prefix}/{self._client_id}/load"
        self._power_off_topic = f"{telemetry_prefix}/{self._client_id}/powerOff"
        # Status topics already set above; command topics use command_prefix
        self._set_temp_cmd_topic = f"{command_prefix}/{self._client_id}/setTemp"
        self._power_off_cmd_topic = f"{command_prefix}/{self._client_id}/powerOff"
        self._mode_cmd_topic = f"{command_prefix}/{self._client_id}/mode"
        self._mode_topic = f"{telemetry_prefix}/{self._client_id}/mode"
        self._attr_unique_id = f"terneo_{self._client_id}"
        self._attr_name = f"Terneo {self._client_id}"
        # Initialize from coordinator data
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._floor_temp = None
        self._air_temp = None
        self._power_off = None
        self._load = None
        self._mode = None  # 0 = auto, 1 = manual
        self._optimistic_mode = None
        self._optimistic_task = None

    def _reset_optimistic_mode(self) -> None:
        """Reset optimistic mode after timeout."""
        self._optimistic_mode = None
        self._optimistic_task = None
        self._update_hvac_mode_from_temps()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Listen to coordinator updates."""
        await super().async_added_to_hass()

        # Restore previous state
        old_state = await self.async_get_last_state()
        if old_state is not None:
            if old_state.attributes.get("temperature") is not None:
                self._attr_target_temperature = old_state.attributes.get("temperature")
            if old_state.state in [
                climate.HVACMode.HEAT,
                climate.HVACMode.AUTO,
                climate.HVACMode.OFF,
            ]:
                self._attr_hvac_mode = old_state.state
            if old_state.attributes.get("power_off") is not None:
                self._power_off = int(old_state.attributes.get("power_off"))
            if old_state.attributes.get("load") is not None:
                self._load = int(old_state.attributes.get("load"))

        # Seed state from coordinator cache to avoid stale restore values on startup
        cached_power_off = self.coordinator.get_value("powerOff")
        cached_load = self.coordinator.get_value("load")
        cached_set_temp = self.coordinator.get_value("setTemp")
        cached_floor_temp = self.coordinator.get_value("floorTemp")
        cached_air_temp = self.coordinator.get_value("airTemp")

        if cached_power_off is not None:
            self._power_off = int(cached_power_off)
        if cached_load is not None:
            self._load = int(cached_load)
        if cached_set_temp is not None:
            self._attr_target_temperature = float(cached_set_temp)
        if cached_floor_temp is not None:
            self._floor_temp = float(cached_floor_temp)
        if cached_air_temp is not None:
            self._air_temp = float(cached_air_temp)

        if (
            cached_power_off is not None
            or cached_load is not None
            or cached_set_temp is not None
            or cached_floor_temp is not None
            or cached_air_temp is not None
        ):
            self._update_hvac_mode_from_temps()
            self.async_write_ha_state()

        # Seed state from coordinator cache to avoid stale restore values on startup
        cached_power_off = self.coordinator.get_value("powerOff")
        cached_load = self.coordinator.get_value("load")
        cached_set_temp = self.coordinator.get_value("setTemp")
        cached_floor_temp = self.coordinator.get_value("floorTemp")
        cached_air_temp = self.coordinator.get_value("airTemp")

        if cached_power_off is not None:
            self._power_off = int(cached_power_off)
        if cached_load is not None:
            self._load = int(cached_load)
        if cached_set_temp is not None:
            self._attr_target_temperature = float(cached_set_temp)
        if cached_floor_temp is not None:
            self._floor_temp = float(cached_floor_temp)
        if cached_air_temp is not None:
            self._air_temp = float(cached_air_temp)

        if (
            cached_power_off is not None
            or cached_load is not None
            or cached_set_temp is not None
            or cached_floor_temp is not None
            or cached_air_temp is not None
        ):
            self._update_hvac_mode_from_temps()
            self.async_write_ha_state()

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{DOMAIN}_{self._client_id}_update",
            self._handle_coordinator_update,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from dispatcher."""
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
        await super().async_will_remove_from_hass()
        if self._optimistic_task:
            self._optimistic_task.cancel()

    @callback
    def _handle_coordinator_update(self, key: str, value: Any) -> None:
        """Handle update from coordinator."""
        if key in ["floorTemp", "airTemp", "setTemp", "load", "powerOff", "mode"]:
            self._handle_message_update(key, value)

    @callback
    def _handle_message_update(self, key: str, value: Any) -> None:
        """Handle message update from coordinator."""
        handlers = {
            "airTemp": self._handle_air_temp,
            "floorTemp": self._handle_floor_temp,
            "setTemp": self._handle_set_temp,
            "load": self._handle_load,
            "powerOff": self._handle_power_off,
            "mode": self._handle_mode,
        }
        handler = handlers.get(key)
        if handler is None:
            return
        try:
            handler(value)
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid value in update: %s", value)

    def _clear_optimistic_mode(self) -> None:
        """Clear optimistic mode and any pending reset."""
        if self._optimistic_task:
            self._optimistic_task.cancel()
            self._optimistic_task = None
        self._optimistic_mode = None

    def _handle_air_temp(self, value: Any) -> None:
        """Handle air temperature update."""
        self._air_temp = float(value)
        self._attr_current_temperature = self._air_temp

    def _handle_floor_temp(self, value: Any) -> None:
        """Handle floor temperature update."""
        self._floor_temp = float(value)
        self._update_hvac_mode_from_temps()

    def _handle_set_temp(self, value: Any) -> None:
        """Handle target temperature update."""
        self._attr_target_temperature = float(value)
        self._update_hvac_mode_from_temps()

    def _handle_load(self, value: Any) -> None:
        """Handle heating load update."""
        self._load = int(value)
        if (self._optimistic_mode == climate.HVACMode.HEAT and self._load == 1) or (
            self._optimistic_mode == climate.HVACMode.AUTO and self._load == 0
        ):
            self._clear_optimistic_mode()
        self._update_hvac_mode_from_temps()

    def _handle_power_off(self, value: Any) -> None:
        """Handle power-off update."""
        self._power_off = int(value)
        if self._power_off == 1 and self._optimistic_mode is not None:
            self._clear_optimistic_mode()
        self._update_hvac_mode_from_temps()

    def _handle_mode(self, value: Any) -> None:
        """Handle mode update."""
        self._mode = int(value)
        self._update_hvac_mode_from_temps()

    def _update_hvac_mode_from_temps(self) -> None:
        """Update hvac_mode and hvac_action based on powerOff, load and temperatures."""
        # If optimistic mode is set, use it instead of calculating
        if self._optimistic_mode is not None:
            self._attr_hvac_mode = self._optimistic_mode
            if self._optimistic_mode == climate.HVACMode.HEAT:
                self._attr_hvac_action = climate.HVACAction.HEATING
            elif self._optimistic_mode == climate.HVACMode.OFF:
                self._attr_hvac_action = climate.HVACAction.OFF
            elif self._optimistic_mode == climate.HVACMode.AUTO:
                self._attr_hvac_action = climate.HVACAction.IDLE
            return

        # hvac_mode is based on powerOff, load and temperatures
        hvac_state = self._calculate_hvac_state()
        if hvac_state is not None:
            self._attr_hvac_mode, self._attr_hvac_action = hvac_state

        # Set current temperature
        if self._air_temp is not None:
            self._attr_current_temperature = self._air_temp
        elif self._floor_temp is not None:
            self._attr_current_temperature = self._floor_temp

    def _calculate_hvac_state(self) -> tuple[str, str] | None:
        """Calculate hvac_mode and hvac_action, or None if state is unknown."""
        power_off = self._power_off
        load = self._load
        hvac_state: tuple[str, str] | None = None

        if power_off is None:
            return None

        if power_off == 1:
            hvac_state = (climate.HVACMode.OFF, climate.HVACAction.OFF)
        elif power_off == 0:
            heating_needed = self._is_heating_needed()
            if not heating_needed:
                hvac_state = (climate.HVACMode.AUTO, climate.HVACAction.IDLE)
            elif load == 1:
                hvac_state = (climate.HVACMode.HEAT, climate.HVACAction.HEATING)
            else:
                hvac_state = (climate.HVACMode.AUTO, climate.HVACAction.IDLE)
        else:
            # Unknown power_off state, default to OFF
            hvac_state = (climate.HVACMode.OFF, climate.HVACAction.OFF)

        return hvac_state

    def _is_heating_needed(self) -> bool:
        """Check if heating is needed based on target and current temperatures."""
        if self._attr_target_temperature is None or self._floor_temp is None:
            return True  # Assume heating needed if temperatures unknown
        return self._attr_target_temperature > self._floor_temp

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.debug("Setting temperature to %s", temperature)
            # Get current values from local state
            current_hvac_mode = self._attr_hvac_mode
            floor_temp = self._floor_temp
            power_off = self._power_off

            # If currently OFF, switch to HEAT when setting temperature
            if current_hvac_mode == climate.HVACMode.OFF:
                _LOGGER.debug("Switching to HEAT mode for temperature setting")
                await self.coordinator.publish_command("mode", "1")
                await self.coordinator.publish_command("powerOff", "0")
                self._power_off = 0  # Update local state
                self._mode = 1  # Update local state
                self._load = 1  # Optimistically assume heating starts
                self._attr_hvac_mode = climate.HVACMode.HEAT
            await self.coordinator.publish_command("setTemp", str(temperature))
            # Optimistically update the state
            self._attr_target_temperature = temperature

            # If temperature is below floor temp, optimistically set to AUTO
            if floor_temp is not None and temperature < floor_temp and power_off == 0:
                self._optimistic_mode = climate.HVACMode.AUTO
                if self._optimistic_task:
                    self._optimistic_task.cancel()
                self._optimistic_task = self.hass.loop.create_task(
                    self._delay_reset_optimistic_mode(60)
                )
            # If currently AUTO and temperature is above floor temp, optimistically set to HEAT
            elif (
                floor_temp is not None
                and temperature > floor_temp
                and power_off == 0
                and current_hvac_mode == climate.HVACMode.AUTO
            ):
                self._optimistic_mode = climate.HVACMode.HEAT
                if self._optimistic_task:
                    self._optimistic_task.cancel()
                self._optimistic_task = self.hass.loop.create_task(
                    self._delay_reset_optimistic_mode(60)
                )

            # Update mode based on new temperature
            self._update_hvac_mode_from_temps()
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new HVAC mode."""
        _LOGGER.debug("Setting HVAC mode to %s", hvac_mode)
        if hvac_mode == climate.HVACMode.HEAT:
            # Set to manual mode (1) and turn on
            await self.coordinator.publish_command("mode", "1")
            await self.coordinator.publish_command("powerOff", "0")
            # Set optimistic mode for 60 seconds
            self._optimistic_mode = climate.HVACMode.HEAT
            if self._optimistic_task:
                self._optimistic_task.cancel()
            self._optimistic_task = self.hass.loop.create_task(
                self._delay_reset_optimistic_mode(60)
            )
        elif hvac_mode == climate.HVACMode.AUTO:
            # Turn on (leave current mode as is)
            await self.coordinator.publish_command("powerOff", "0")
            # Reset optimistic mode
            if self._optimistic_task:
                self._optimistic_task.cancel()
                self._optimistic_task = None
            self._optimistic_mode = None
        elif hvac_mode == climate.HVACMode.OFF:
            await self.coordinator.publish_command("powerOff", "1")
            # Reset optimistic mode
            if self._optimistic_task:
                self._optimistic_task.cancel()
                self._optimistic_task = None
            self._optimistic_mode = None
        else:
            return
        # Optimistically update the state
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def _delay_reset_optimistic_mode(self, delay: int) -> None:
        """Delay resetting optimistic mode."""
        await asyncio.sleep(delay)
        self._reset_optimistic_mode()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for restore."""
        attrs: dict[str, Any] = {}
        if self._power_off is not None:
            attrs["power_off"] = self._power_off
        if self._load is not None:
            attrs["load"] = self._load
        return attrs

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._client_id)},
            "name": f"Terneo {self._client_id}",
            "manufacturer": "Terneo",
            "model": self._model,
        }
