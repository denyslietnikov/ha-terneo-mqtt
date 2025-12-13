"""Test TerneoMQ climate entity."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.terneo_mqtt.climate import TerneoMQTTClimate


@pytest.mark.asyncio
async def test_climate_entity_creation() -> None:
    """Test climate entity initialization."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")

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
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

    # Test air temp message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/airTemp",
        payload="22.5",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/airTemp",
        timestamp=1234567890
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
        timestamp=1234567890
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
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "idle"  # Default when power on
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test load message (heating on)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "heat"
    assert entity._attr_hvac_action == "idle"  # Default when power on
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
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_action == "heating"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test floor temp message (set floor to 20.0, which equals target of 20.0)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="20.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    # hvac_mode should be AUTO since floor temp (20.0) >= target temp (20.0)
    assert entity._attr_hvac_mode == "auto"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test set temp message (set to 25.0, higher than floor 20.0)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/setTemp",
        payload="25.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/setTemp",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity._attr_target_temperature == 25.0
    assert entity._attr_hvac_mode == "heat"  # setTemp=25.0 > floorTemp=20.0
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
        timestamp=1234567890
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
        timestamp=1234567890
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
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "heat"  # load=1 overrides mode
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test mode message (manual mode)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/mode",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/mode",
        timestamp=1234567890
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
        timestamp=1234567890
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
        timestamp=1234567890
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
        timestamp=1234567890
    )
    entity._handle_message(msg)

    # Should still stay OFF
    assert entity._attr_hvac_mode == "off"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_mode_changes_when_load_off() -> None:
    """Test that mode changes work when load is off."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

    # Turn device on
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890
    )
    entity._handle_message(msg)
    assert entity._attr_hvac_mode == "heat"

    # Set load to 0 (not heating)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890
    )
    entity._handle_message(msg)
    assert entity._attr_hvac_action == "idle"

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Now set mode to auto (0)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/mode",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/mode",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity._attr_hvac_mode == "auto"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_without_air_temp_uses_floor_temp() -> None:
    """Test that when air temp is not supported, floor temp is used as current temp."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo", supports_air_temp=False)

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

    # Set floor temp
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="22.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    # Should use floor temp as current temp since air temp not supported
    assert entity._attr_current_temperature == 22.0
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.climate.mqtt')
async def test_climate_async_set_hvac_mode_heat_from_off(mock_mqtt) -> None:
    """Test setting HVAC mode to HEAT from OFF."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")
    entity.hass = hass
    entity.async_write_ha_state = AsyncMock()
    # Set to OFF first
    entity._attr_hvac_mode = "off"

    await entity.async_set_hvac_mode("heat")

    # Should publish powerOff=0 and mode=1
    assert mock_mqtt.async_publish.call_count == 2
    mock_mqtt.async_publish.assert_any_call(hass, entity._power_off_cmd_topic, "0", retain=True)
    mock_mqtt.async_publish.assert_any_call(hass, entity._mode_cmd_topic, "1", retain=True)
    assert entity.hvac_mode == "heat"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.climate.mqtt')
async def test_climate_async_set_hvac_mode_auto_from_off(mock_mqtt) -> None:
    """Test setting HVAC mode to AUTO from OFF."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")
    entity.hass = hass
    entity.async_write_ha_state = AsyncMock()
    # Set to OFF first
    entity._attr_hvac_mode = "off"

    await entity.async_set_hvac_mode("auto")

    # Should publish powerOff=0 and mode=0
    assert mock_mqtt.async_publish.call_count == 2
    mock_mqtt.async_publish.assert_any_call(hass, entity._power_off_cmd_topic, "0", retain=True)
    mock_mqtt.async_publish.assert_any_call(hass, entity._mode_cmd_topic, "0", retain=True)
    assert entity.hvac_mode == "auto"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.climate.mqtt')
async def test_climate_async_set_temperature(mock_mqtt) -> None:
    """Test setting temperature."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")
    entity.hass = hass
    entity.async_write_ha_state = AsyncMock()
    # Set initial state
    entity._attr_hvac_mode = "heat"

    await entity.async_set_temperature(temperature=25.0)

    # Should publish setTemp
    assert mock_mqtt.async_publish.call_count == 1
    mock_mqtt.async_publish.assert_called_once_with(hass, entity._set_temp_cmd_topic, "25.0", retain=True)
    assert entity._attr_target_temperature == 25.0
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_climate_auto_mode_switches_to_heat_when_load_starts() -> None:
    """Test that AUTO mode switches to HEAT when device starts heating (load=1)."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

    # Set initial state: AUTO mode (powerOff=0, mode=0, load=0)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/mode",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/mode",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890
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
        timestamp=1234567890
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
        timestamp=1234567890
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
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")

    device_info = entity.device_info
    assert device_info["identifiers"] == {("terneo", "terneo_ax_1B0026")}
    assert device_info["name"] == "Terneo terneo_ax_1B0026"
    assert device_info["manufacturer"] == "Terneo"
    assert device_info["model"] == "AX"


@pytest.mark.asyncio
async def test_climate_hvac_mode_based_on_temperature_comparison() -> None:
    """Test that hvac_mode changes from HEAT to AUTO when target temp is lowered below floor temp."""
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

    # Device is ON
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    # Set floor temp to 21°C
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="21.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    # Set target temp to 23°C (above floor temp, should be HEAT mode)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/setTemp",
        payload="23.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/setTemp",
        timestamp=1234567890
    )
    entity._handle_message(msg)
    assert entity._attr_hvac_mode == "heat"

    # Load turns ON (heating actively)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890
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
        timestamp=1234567890
    )
    entity._handle_message(msg)
    
    # Load turns OFF (target reached, no heating needed)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    # Should switch to AUTO mode since floor temp (21) >= target temp (20)
    assert entity._attr_hvac_mode == "auto"
    assert entity._attr_hvac_action == "idle"
    entity.async_write_ha_state.assert_called()