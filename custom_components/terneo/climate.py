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
    prefix = config_entry.options.get(
        "topic_prefix", config_entry.data.get("prefix", "terneo")
    )
    supports_air_temp = config_entry.options.get("supports_air_temp", True)
    model = config_entry.options.get("model", config_entry.data.get("model", "AX"))
    entities = []
    coordinators = {}
    for device in devices:
        client_id = device["client_id"]
        coordinator = TerneoCoordinator(hass, client_id, prefix, supports_air_temp)
        coordinators[client_id] = coordinator
        await coordinator.async_setup()
        entities.append(TerneoMQTTClimate(hass, coordinator, model))
    if entities:
        async_add_entities(entities)


class TerneoMQTTClimate(ClimateEntity):
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
        topic_prefix = coordinator.prefix
        self._air_temp_topic = f"{topic_prefix}/{self._client_id}/airTemp"
        self._floor_temp_topic = f"{topic_prefix}/{self._client_id}/floorTemp"
        self._set_temp_topic = f"{topic_prefix}/{self._client_id}/setTemp"
        self._load_topic = f"{topic_prefix}/{self._client_id}/load"
        self._power_off_topic = f"{topic_prefix}/{self._client_id}/powerOff"
        # Command topics
        self._set_temp_cmd_topic = f"{topic_prefix}/{self._client_id}/setTemp"
        self._power_off_cmd_topic = f"{topic_prefix}/{self._client_id}/powerOff"
        self._mode_cmd_topic = f"{topic_prefix}/{self._client_id}/mode"
        self._mode_topic = f"{topic_prefix}/{self._client_id}/mode"
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
        try:
            updated = False
            if key == "airTemp":
                self._air_temp = float(value)
                self._attr_current_temperature = float(value)
                updated = True
            elif key == "floorTemp":
                self._floor_temp = float(value)
                # Update hvac_mode based on setTemp vs floorTemp
                self._update_hvac_mode_from_temps()
                updated = True
            elif key == "setTemp":
                self._attr_target_temperature = float(value)
                # Update hvac_mode based on setTemp vs floorTemp
                self._update_hvac_mode_from_temps()
                updated = True
            elif key == "load":
                self._load = int(value)
                # Reset optimistic mode based on real state change
                if self._optimistic_mode == climate.HVACMode.HEAT and self._load == 1:
                    # Device started heating, HEAT is now real
                    if self._optimistic_task:
                        self._optimistic_task.cancel()
                        self._optimistic_task = None
                    self._optimistic_mode = None
                elif self._optimistic_mode == climate.HVACMode.AUTO and self._load == 0:
                    # Device stopped heating, AUTO is now real
                    if self._optimistic_task:
                        self._optimistic_task.cancel()
                        self._optimistic_task = None
                    self._optimistic_mode = None
                self._update_hvac_mode_from_temps()
                updated = True
            elif key == "powerOff":
                self._power_off = int(value)
                self._update_hvac_mode_from_temps()
                updated = True
            elif key == "mode":
                self._mode = int(value)
                self._update_hvac_mode_from_temps()
                updated = True

            if updated:
                self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid value in update: %s", value)

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

        # Get current values from coordinator
        power_off = self._power_off
        load = self._load
        floor_temp = self._floor_temp
        air_temp = self._air_temp

        # hvac_mode is based on powerOff, load and temperatures
        if power_off == 1:
            self._attr_hvac_mode = climate.HVACMode.OFF
            self._attr_hvac_action = climate.HVACAction.OFF
        elif power_off == 0:
            # Check if heating is needed based on temperatures
            heating_needed = self._is_heating_needed()
            if not heating_needed or load == 0:
                self._attr_hvac_mode = climate.HVACMode.AUTO
                self._attr_hvac_action = climate.HVACAction.IDLE
            elif load == 1:
                self._attr_hvac_mode = climate.HVACMode.HEAT
                self._attr_hvac_action = climate.HVACAction.HEATING
            else:
                # Unknown load state, default to AUTO
                self._attr_hvac_mode = climate.HVACMode.AUTO
                self._attr_hvac_action = climate.HVACAction.IDLE
        else:
            # Unknown power_off state, default to OFF
            self._attr_hvac_mode = climate.HVACMode.OFF
            self._attr_hvac_action = climate.HVACAction.OFF

        # Set current temperature
        if air_temp is not None:
            self._attr_current_temperature = air_temp
        elif floor_temp is not None:
            self._attr_current_temperature = floor_temp

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
                await self.coordinator.publish_command("mode", "3")
                await self.coordinator.publish_command("powerOff", "0")
                self._power_off = 0  # Update local state
                self._mode = 3  # Update local state
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

            # Update mode based on new temperature
            self._update_hvac_mode_from_temps()
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new HVAC mode."""
        _LOGGER.debug("Setting HVAC mode to %s", hvac_mode)
        if hvac_mode == climate.HVACMode.HEAT:
            # Set to manual mode (3) and turn on
            await self.coordinator.publish_command("mode", "3")
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
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._client_id)},
            "name": f"Terneo {self._client_id}",
            "manufacturer": "Terneo",
            "model": self._model,
        }
