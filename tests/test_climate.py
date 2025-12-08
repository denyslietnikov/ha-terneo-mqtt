"""Test Terneo MQTT climate entity."""
from unittest.mock import AsyncMock, MagicMock

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
    assert entity._set_temp_topic == "terneo/terneo_ax_1B0026/setTemp"
    assert entity._load_topic == "terneo/terneo_ax_1B0026/load"
    assert entity.unique_id == "terneo_terneo_ax_1B0026"
    assert entity.name == "Terneo terneo_ax_1B0026"


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

    assert entity._attr_hvac_mode == "heat"
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