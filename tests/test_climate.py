"""Test Terneo MQTT climate entity."""
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

    # Test floor temp message (set floor to 20.0)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="20.0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    # Since setTemp is 20.0 (from earlier), and floorTemp=20.0, should switch to AUTO
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


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.climate.mqtt')
async def test_climate_async_set_hvac_mode_auto(mock_mqtt) -> None:
    """Test setting HVAC mode to AUTO (idle)."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoMQTTClimate(hass, "terneo_ax_1B0026", "terneo")
    entity.hass = hass
    entity.async_write_ha_state = AsyncMock()
    # Set temps: setTemp=25.0, floorTemp=20.0 → should switch to HEAT
    entity._attr_target_temperature = 25.0
    entity._floor_temp = 20.0

    await entity.async_set_hvac_mode("auto")

    mock_mqtt.async_publish.assert_called_once_with(hass, entity._power_off_cmd_topic, "0", retain=True)
    assert entity.hvac_mode == "heat"  # Because setTemp > floorTemp
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