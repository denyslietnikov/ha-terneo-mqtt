"""Test TerneoMQ climate entity."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.mqtt import ReceiveMessage

from custom_components.terneo.climate import TerneoMQTTClimate


@pytest.mark.asyncio
async def test_climate_entity_creation() -> None:
    """Test climate entity initialization."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._topic_prefix == "terneo"
    assert entity._air_temp_topic == "terneo/terneo_ax_1B0026/airTemp"
    assert entity._floor_temp_topic == "terneo/terneo_ax_1B0026/floorTemp"
    assert entity._set_temp_topic == "terneo/terneo_ax_1B0026/setTemp"
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
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Test air temp message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/airTemp",
        payload="22.5",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/airTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_current_temperature == 22.5
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test set temp message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/setTemp",
        payload="20.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/setTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_target_temperature == 20.0
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # First set powerOff to 0 (turn on)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"  # AUTO when load=0
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test load message (heating on)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_action == "heating"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test floor temp message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="19.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # hvac_mode should remain HEAT since load=1 and heating is needed (setTemp=20.0 > floorTemp=19.0)
    assert entity._attr_hvac_mode == "heat"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test set temp message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/setTemp",
        payload="25.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/setTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_target_temperature == 25.0
    assert entity._attr_hvac_mode == "heat"  # remains HEAT since load=1
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test powerOff message (off)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "off"
    assert entity._attr_hvac_action == "off"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Turn device back on before testing mode
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "heat"  # Default when turned on
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test mode message (auto mode)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/mode",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/mode",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "heat"  # load=1 overrides mode
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test mode message (manual mode)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/mode",
        payload="3",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/mode",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "heat"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Turn device off again for final test
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "off"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test that temperatures don't change mode when OFF
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="20.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should stay OFF
    assert entity._attr_hvac_mode == "off"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/setTemp",
        payload="25.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/setTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should still stay OFF
    assert entity._attr_hvac_mode == "off"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_mode_changes_when_load_off() -> None:
    """Test that hvac_mode changes based on load and powerOff."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Initially OFF
    assert entity._attr_hvac_mode == "off"

    # Turn device on, load=0 -> AUTO
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"

    # Set load to 1 (heating) -> HEAT
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)
    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "heating"

    # Set load back to 0 -> AUTO
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"

    # Turn OFF
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)
    assert entity._attr_hvac_mode == "off"
    assert entity._attr_hvac_action == "off"


@pytest.mark.asyncio
async def test_climate_without_air_temp_uses_floor_temp() -> None:
    """Test that when air temp is not supported, floor temp is used as current temp."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(
        hass, "terneo_ax_1B0026", "terneo", supports_air_temp=False
    )

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Set floor temp
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="22.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should use floor temp as current temp since air temp not supported
    assert entity._attr_current_temperature == 22.0
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch("custom_components.terneo.climate.mqtt")
async def test_climate_async_set_hvac_mode_heat_from_off(mock_mqtt) -> None:
    """Test setting HVAC mode to HEAT from OFF."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    # Set to OFF first
    entity._attr_hvac_mode = "off"

    await entity.async_set_hvac_mode("heat")

    # Should publish mode=3 and powerOff=0 to turn on the device
    assert mock_mqtt.async_publish.call_count == 2
    mock_mqtt.async_publish.assert_any_call(
        hass, entity._mode_cmd_topic, "3", retain=False
    )
    mock_mqtt.async_publish.assert_any_call(
        hass, entity._power_off_cmd_topic, "0", retain=False
    )
    assert entity.hvac_mode == "heat"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch("custom_components.terneo.climate.mqtt")
async def test_climate_async_set_hvac_mode_auto_from_off(mock_mqtt) -> None:
    """Test setting HVAC mode to AUTO from OFF."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    # Set to OFF first
    entity._attr_hvac_mode = "off"

    await entity.async_set_hvac_mode("auto")

    # Should publish powerOff=0 (leave mode as is)
    assert mock_mqtt.async_publish.call_count == 1
    mock_mqtt.async_publish.assert_called_once_with(
        hass, entity._power_off_cmd_topic, "0", retain=False
    )
    assert entity.hvac_mode == "auto"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch("custom_components.terneo.climate.mqtt")
async def test_climate_async_set_temperature(mock_mqtt) -> None:
    """Test setting temperature."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    # Set initial state
    entity._attr_hvac_mode = "heat"

    await entity.async_set_temperature(temperature=25.0)

    # Should publish setTemp
    assert mock_mqtt.async_publish.call_count == 1
    mock_mqtt.async_publish.assert_called_once_with(
        hass, entity._set_temp_cmd_topic, "25.0", retain=False
    )
    assert entity._attr_target_temperature == 25.0
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch("custom_components.terneo.climate.mqtt")
async def test_climate_async_set_temperature_from_off(mock_mqtt) -> None:
    """Test setting temperature when device is OFF."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    # Set initial state to OFF
    entity._attr_hvac_mode = "off"

    await entity.async_set_temperature(temperature=25.0)

    # Should publish mode=3, powerOff=0, and setTemp
    assert mock_mqtt.async_publish.call_count == 3
    mock_mqtt.async_publish.assert_any_call(
        hass, entity._mode_cmd_topic, "3", retain=False
    )
    mock_mqtt.async_publish.assert_any_call(
        hass, entity._power_off_cmd_topic, "0", retain=False
    )
    mock_mqtt.async_publish.assert_any_call(
        hass, entity._set_temp_cmd_topic, "25.0", retain=False
    )
    assert entity._attr_target_temperature == 25.0
    assert entity._attr_hvac_mode == "heat"
    entity.async_write_ha_state.assert_called_once()
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_auto_mode_switches_to_heat_when_load_starts() -> None:
    """Test that AUTO mode switches to HEAT when device starts heating (load=1)."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Set initial state: AUTO mode (powerOff=0, mode=0, load=0)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/mode",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/mode",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"
    entity.async_write_ha_state.assert_called()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Device starts heating: load=1
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should switch to HEAT mode when actively heating
    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "heating"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Device stops heating: load=0
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should switch back to AUTO mode when not heating
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_device_info() -> None:
    """Test device info."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")

    device_info = entity.device_info
    assert device_info["identifiers"] == {("terneo", "terneo_ax_1B0026")}
    assert device_info["name"] == "Terneo terneo_ax_1B0026"
    assert device_info["manufacturer"] == "Terneo"
    assert device_info["model"] == "AX"


@pytest.mark.asyncio
async def test_climate_hvac_mode_based_on_temperature_comparison() -> None:
    """Test that hvac_mode changes based on load status regardless of temperatures."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Device is ON
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Set floor temp to 21°C
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="21.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Set target temp to 23°C (above floor temp, but hvac_mode depends only on load)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/setTemp",
        payload="23.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/setTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)
    # Initially load=0 -> AUTO
    assert entity._attr_hvac_mode == "auto"

    # Load turns ON (heating actively) -> HEAT
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)
    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "heating"

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Now lower target temp to 20°C (below floor temp of 21°C)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/setTemp",
        payload="20.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/setTemp",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Load turns OFF (target reached, no heating needed) -> AUTO
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should be AUTO mode since load=0
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"
    entity.async_write_ha_state.assert_called()


@pytest.mark.asyncio
@patch("custom_components.terneo.climate.mqtt")
async def test_climate_optimistic_mode_heat(mock_mqtt) -> None:
    """Test optimistic mode when setting HEAT from OFF."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")
    entity.hass = hass
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
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should still be HEAT due to optimistic mode
    assert entity._attr_hvac_mode == "heat"
    assert entity._optimistic_mode == "heat"  # Not reset yet

    # Simulate load=0 message (device hasn't started heating yet)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should still be HEAT due to optimistic mode (load=0 doesn't reset it)
    assert entity._attr_hvac_mode == "heat"
    assert entity._optimistic_mode == "heat"

    # Simulate load=1 message (device started heating)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should still be HEAT, and optimistic mode reset since load=1 confirms heating
    assert entity._attr_hvac_mode == "heat"
    assert entity._optimistic_mode is None
    assert entity._optimistic_task is None


@pytest.mark.asyncio
@patch("custom_components.terneo.climate.mqtt")
async def test_climate_optimistic_mode_temperature_auto(mock_mqtt) -> None:
    """Test optimistic mode when setting temperature below floor temp."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", True, "AX")
    entity.hass = hass
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
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should still be AUTO due to optimistic mode (load=1 doesn't reset AUTO optimistic)
    assert entity._attr_hvac_mode == "auto"
    assert entity._optimistic_mode == "auto"

    # Simulate load=0 message (device stopped heating)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    # Should still be AUTO, and optimistic mode reset since load=0 confirms AUTO
    assert entity._attr_hvac_mode == "auto"
    assert entity._optimistic_mode is None
    assert entity._optimistic_task is None
