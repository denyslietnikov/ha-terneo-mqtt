"""Test TerneoMQ climate entity."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.terneo.climate import TerneoMQTTClimate


@pytest.mark.asyncio
async def test_climate_entity_creation() -> None:
    """Test climate entity initialization."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoMQTTClimate(hass, coordinator, "AX")

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._supports_air_temp is True
    assert entity._load_topic == "terneo/terneo_ax_1B0026/load"
    assert entity._power_off_topic == "terneo/terneo_ax_1B0026/powerOff"
    assert entity.unique_id == "terneo_terneo_ax_1B0026"
    assert entity.name == "Terneo terneo_ax_1B0026"
    assert entity.hvac_modes == ["heat", "off", "auto"]
    assert entity._attr_hvac_mode == "off"
    assert entity._attr_hvac_action == "off"


@pytest.mark.asyncio
async def test_climate_mqtt_message_handling() -> None:
    """Test MQTT message handling."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.get_value.return_value = None
    entity = TerneoMQTTClimate(hass, coordinator, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Test air temp message
    entity._handle_coordinator_update("airTemp", 22.5)

    assert entity._attr_current_temperature == 22.5
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test set temp message
    entity._handle_coordinator_update("setTemp", 20.0)

    assert entity._attr_target_temperature == 20.0
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # First set powerOff to 0 (turn on)
    entity._handle_coordinator_update("powerOff", 0)

    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"  # AUTO when load=0
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test load message (heating on)
    entity._handle_coordinator_update("load", 1)

    assert entity._attr_hvac_action == "heating"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test floor temp message
    entity._handle_coordinator_update("floorTemp", 19.0)

    # hvac_mode should remain HEAT since load=1 and heating is needed (setTemp=20.0 > floorTemp=19.0)
    assert entity._attr_hvac_mode == "heat"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test set temp message
    entity._handle_coordinator_update("setTemp", 25.0)

    assert entity._attr_target_temperature == 25.0
    assert entity._attr_hvac_mode == "heat"  # remains HEAT since load=1
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Drop target temp below floor temp -> AUTO even if load is 1
    entity._handle_coordinator_update("setTemp", 18.0)

    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test powerOff message (off)
    entity._handle_coordinator_update("powerOff", 1)

    assert entity._attr_hvac_mode == "off"
    assert entity._attr_hvac_action == "off"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Turn device back on before testing mode
    entity._handle_coordinator_update("powerOff", 0)

    assert entity._attr_hvac_mode == "auto"  # setTemp=18.0 below floorTemp=19.0
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test mode message (auto mode)
    entity._handle_coordinator_update("mode", 0)

    assert entity._attr_hvac_mode == "auto"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test mode message (manual mode)
    entity._handle_coordinator_update("mode", 1)

    assert entity._attr_hvac_mode == "auto"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Turn device off again for final test
    entity._handle_coordinator_update("powerOff", 1)

    assert entity._attr_hvac_mode == "off"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test that temperatures don't change mode when OFF
    entity._handle_coordinator_update("floorTemp", 20.0)

    # Should stay OFF
    assert entity._attr_hvac_mode == "off"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test setTemp update when OFF
    entity._handle_coordinator_update("setTemp", 25.0)

    # Should still stay OFF
    assert entity._attr_hvac_mode == "off"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_mode_changes_when_load_off() -> None:
    """Test that hvac_mode changes based on load and powerOff."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoMQTTClimate(hass, coordinator, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Initially OFF
    assert entity._attr_hvac_mode == "off"

    # Turn device on, load=0 -> AUTO
    entity._handle_coordinator_update("powerOff", 0)
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"

    # Set load to 1 (heating) -> HEAT
    entity._handle_coordinator_update("load", 1)
    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "heating"

    # Set load back to 0 -> AUTO
    entity._handle_coordinator_update("load", 0)
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"

    # Turn OFF
    entity._handle_coordinator_update("powerOff", 1)
    assert entity._attr_hvac_mode == "off"
    assert entity._attr_hvac_action == "off"


@pytest.mark.asyncio
async def test_climate_without_air_temp_uses_floor_temp() -> None:
    """Test that when air temp is not supported, floor temp is used as current temp."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = False
    entity = TerneoMQTTClimate(hass, coordinator, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Set floor temp
    entity._handle_coordinator_update("floorTemp", 22.0)

    # Should use floor temp as current temp since air temp not supported
    assert entity._attr_current_temperature == 22.0
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_does_not_force_off_when_power_off_unknown() -> None:
    """Test that unknown powerOff doesn't force OFF on startup."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoMQTTClimate(hass, coordinator, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Simulate restored state before MQTT values arrive
    entity._attr_hvac_mode = "heat"
    entity._attr_hvac_action = "heating"

    # floorTemp arrives before powerOff/load
    entity._handle_coordinator_update("floorTemp", 20.0)

    # Should keep restored state rather than forcing OFF
    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "heating"


@pytest.mark.asyncio
async def test_climate_async_set_hvac_mode_heat_from_off() -> None:
    """Test setting HVAC mode to HEAT from OFF."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()
    # Set to OFF first
    entity._attr_hvac_mode = "off"

    await entity.async_set_hvac_mode("heat")

    # Should publish mode=1 and powerOff=0 to turn on the device
    assert coordinator.publish_command.call_count == 2
    coordinator.publish_command.assert_any_call("mode", "1")
    coordinator.publish_command.assert_any_call("powerOff", "0")
    assert entity._attr_hvac_mode == "heat"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_async_set_hvac_mode_auto_from_off() -> None:
    """Test setting HVAC mode to AUTO from OFF."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()
    # Set to OFF first
    entity._attr_hvac_mode = "off"

    await entity.async_set_hvac_mode("auto")

    # Should publish powerOff=0 (leave mode as is)
    coordinator.publish_command.assert_called_once_with("powerOff", "0")
    assert entity._attr_hvac_mode == "auto"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_power_off_clears_optimistic_mode() -> None:
    """Test powerOff=1 clears optimistic mode immediately."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()

    entity._optimistic_mode = "auto"
    entity._optimistic_task = MagicMock()

    entity._handle_coordinator_update("powerOff", 1)

    assert entity._optimistic_mode is None
    assert entity._optimistic_task is None
    assert entity._attr_hvac_mode == "off"
    assert entity._attr_hvac_action == "off"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_seeds_state_from_coordinator_cache() -> None:
    """Test cached coordinator values override restored state on startup."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.get_value.side_effect = lambda key: {
        "powerOff": 1,
        "load": 0,
        "setTemp": 18.0,
        "floorTemp": 19.4,
        "airTemp": 20.1,
    }.get(key)
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()
    entity.async_get_last_state = AsyncMock(
        return_value=MagicMock(attributes={"temperature": 22.0}, state="auto")
    )

    climate_module = __import__(
        "custom_components.terneo.climate", fromlist=["async_dispatcher_connect"]
    )
    climate_module.async_dispatcher_connect = MagicMock(return_value=MagicMock())

    await entity.async_added_to_hass()

    assert entity._power_off == 1
    assert entity._load == 0
    assert entity._attr_target_temperature == 18.0
    assert entity._floor_temp == 19.4
    assert entity._air_temp == 20.1
    assert entity._attr_hvac_mode == "off"
    assert entity._attr_hvac_action == "off"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_restores_power_off_and_load() -> None:
    """Test restoring powerOff/load from last state attributes."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.get_value.return_value = None
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()
    entity.async_get_last_state = AsyncMock(
        return_value=MagicMock(
            attributes={"temperature": 22.0, "power_off": 1, "load": 0},
            state="auto",
        )
    )

    climate_module = __import__(
        "custom_components.terneo.climate", fromlist=["async_dispatcher_connect"]
    )
    climate_module.async_dispatcher_connect = MagicMock(return_value=MagicMock())

    await entity.async_added_to_hass()

    assert entity._power_off == 1
    assert entity._load == 0
    entity._update_hvac_mode_from_temps()
    assert entity._attr_hvac_mode == "off"
    assert entity._attr_hvac_action == "off"


@pytest.mark.asyncio
async def test_climate_async_set_temperature() -> None:
    """Test setting temperature."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()
    # Set initial state
    entity._attr_hvac_mode = "heat"

    await entity.async_set_temperature(temperature=25.0)

    # Should publish setTemp
    coordinator.publish_command.assert_called_once_with("setTemp", "25.0")
    assert entity._attr_target_temperature == 25.0
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_async_set_temperature_from_off() -> None:
    """Test setting temperature when device is OFF."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()
    # Set initial state to OFF
    entity._attr_hvac_mode = "off"

    await entity.async_set_temperature(temperature=25.0)

    # Should publish mode=3, powerOff=0, and setTemp
    assert coordinator.publish_command.call_count == 3
    coordinator.publish_command.assert_any_call("mode", "1")
    coordinator.publish_command.assert_any_call("powerOff", "0")
    coordinator.publish_command.assert_any_call("setTemp", "25.0")
    assert entity._attr_target_temperature == 25.0
    assert entity._attr_hvac_mode == "heat"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_async_set_temperature_from_auto_optimistic_heat() -> None:
    """Test optimistic HEAT when AUTO and target is above floor temp."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()

    entity._attr_hvac_mode = "auto"
    entity._power_off = 0
    entity._floor_temp = 20.0

    await entity.async_set_temperature(temperature=25.0)

    coordinator.publish_command.assert_called_once_with("setTemp", "25.0")
    assert entity._attr_target_temperature == 25.0
    assert entity._attr_hvac_mode == "heat"
    assert entity._optimistic_mode == "heat"
    assert entity._optimistic_task is not None
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_auto_mode_switches_to_heat_when_load_starts() -> None:
    """Test that AUTO mode switches to HEAT when device starts heating (load=1)."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoMQTTClimate(hass, coordinator, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Set initial state: AUTO mode (powerOff=0, mode=0, load=0)
    entity._handle_coordinator_update("powerOff", 0)
    entity._handle_coordinator_update("mode", 0)
    entity._handle_coordinator_update("load", 0)

    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"
    entity.async_write_ha_state.assert_called()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Device starts heating: load=1
    entity._handle_coordinator_update("load", 1)

    # Should switch to HEAT mode when actively heating
    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "heating"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Device stops heating: load=0
    entity._handle_coordinator_update("load", 0)

    # Should switch back to AUTO mode when not heating
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_device_info() -> None:
    """Test device info."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoMQTTClimate(hass, coordinator, "AX")

    device_info = entity.device_info
    assert device_info["identifiers"] == {("terneo", "terneo_ax_1B0026")}
    assert device_info["name"] == "Terneo terneo_ax_1B0026"
    assert device_info["manufacturer"] == "Terneo"
    assert device_info["model"] == "AX"


@pytest.mark.asyncio
async def test_climate_hvac_mode_based_on_temperature_comparison() -> None:
    """Test hvac_mode based on powerOff, load, and temperature comparison."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoMQTTClimate(hass, coordinator, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Device is ON
    entity._handle_coordinator_update("powerOff", 0)

    # Set floor temp to 21°C
    entity._handle_coordinator_update("floorTemp", 21.0)

    # Set target temp to 23°C (above floor temp)
    entity._handle_coordinator_update("setTemp", 23.0)

    # Initially load=0 -> AUTO
    assert entity._attr_hvac_mode == "auto"

    # Load turns ON (heating actively) -> HEAT
    entity._handle_coordinator_update("load", 1)
    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "heating"

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Now lower target temp to 20°C (below floor temp of 21°C)
    entity._handle_coordinator_update("setTemp", 20.0)

    # Load turns ON but heating not needed -> AUTO
    entity._handle_coordinator_update("load", 1)

    # Should be AUTO mode since heating is not needed
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"
    entity.async_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_climate_optimistic_mode_heat() -> None:
    """Test optimistic mode when setting HEAT from OFF."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()

    # Set initial state to OFF
    entity._power_off = 1
    entity._load = 0
    entity._update_hvac_mode_from_temps()
    assert entity._attr_hvac_mode == "off"

    # Set HEAT mode
    await entity.async_set_hvac_mode("heat")

    # Should be optimistically set to HEAT
    assert entity._attr_hvac_mode == "heat"
    assert entity._optimistic_mode == "heat"
    assert entity._optimistic_task is not None

    # Simulate powerOff=0 message (from the command)
    entity._handle_coordinator_update("powerOff", 0)

    # Should still be HEAT due to optimistic mode
    assert entity._attr_hvac_mode == "heat"
    assert entity._optimistic_mode == "heat"  # Not reset yet

    # Simulate load=0 message (device hasn't started heating yet)
    entity._handle_coordinator_update("load", 0)

    # Should still be HEAT due to optimistic mode (load=0 doesn't reset it)
    assert entity._attr_hvac_mode == "heat"
    assert entity._optimistic_mode == "heat"

    # Simulate load=1 message (device started heating)
    entity._handle_coordinator_update("load", 1)

    # Should still be HEAT, and optimistic mode reset since load=1 confirms heating
    assert entity._attr_hvac_mode == "heat"
    assert entity._optimistic_mode is None
    assert entity._optimistic_task is None


@pytest.mark.asyncio
async def test_climate_optimistic_mode_temperature_auto() -> None:
    """Test optimistic mode when setting temperature below floor temp."""
    hass = MagicMock()
    hass.loop.create_task = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoMQTTClimate(hass, coordinator, "AX")
    entity.async_write_ha_state = MagicMock()

    # Set initial state: ON, heating (load=1), floor temp = 22.0, set temp = 25.0
    entity._power_off = 0
    entity._load = 1
    entity._floor_temp = 22.0
    entity._attr_target_temperature = 25.0
    entity._update_hvac_mode_from_temps()
    assert entity._attr_hvac_mode == "heat"

    # Set temperature below floor temp
    await entity.async_set_temperature(temperature=20.0)

    # Should be optimistically set to AUTO
    assert entity._attr_hvac_mode == "auto"
    assert entity._optimistic_mode == "auto"
    assert entity._optimistic_task is not None
    assert entity._attr_target_temperature == 20.0

    # Simulate load=1 message (device still thinks it should heat)
    entity._handle_coordinator_update("load", 1)

    # Should still be AUTO due to optimistic mode (load=1 doesn't reset AUTO optimistic)
    assert entity._attr_hvac_mode == "auto"
    assert entity._optimistic_mode == "auto"

    # Simulate load=0 message (device stopped heating)
    entity._handle_coordinator_update("load", 0)

    # Should still be AUTO, and optimistic mode reset since load=0 confirms AUTO
    assert entity._attr_hvac_mode == "auto"
    assert entity._optimistic_mode is None
    assert entity._optimistic_task is None
