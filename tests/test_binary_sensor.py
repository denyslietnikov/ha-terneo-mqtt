"""Test TerneoMQ binary sensor entities."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.core import HomeAssistant

from custom_components.terneo_mqtt.binary_sensor import TerneoBinarySensor


@pytest.mark.asyncio
async def test_binary_sensor_entity_creation() -> None:
    """Test binary sensor entity initialization."""
    hass = MagicMock()
    entity = TerneoBinarySensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="heating",
        name="Heating",
        device_class=None,
        topic_suffix="load"
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._topic == "terneo/terneo_ax_1B0026/load"
    assert entity.unique_id == "terneo_ax_1B0026_heating"
    assert entity.name == "Terneo terneo_ax_1B0026 Heating"


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.binary_sensor.mqtt')
async def test_binary_sensor_async_added_to_hass(mock_mqtt) -> None:
    """Test MQTT subscription when entity is added."""
    unsubscribe_mock = MagicMock()
    mock_mqtt.async_subscribe = AsyncMock(return_value=unsubscribe_mock)
    hass = MagicMock()
    entity = TerneoBinarySensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="heating",
        name="Heating",
        device_class=None,
        topic_suffix="load"
    )
    entity.hass = hass

    await entity.async_added_to_hass()

    mock_mqtt.async_subscribe.assert_called_once_with(hass, entity._topic, entity._handle_message, qos=0)
    assert entity._unsubscribe == unsubscribe_mock


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.binary_sensor.mqtt')
async def test_binary_sensor_async_will_remove_from_hass(mock_mqtt) -> None:
    """Test MQTT unsubscription when entity is removed."""
    unsubscribe_mock = MagicMock()
    mock_mqtt.async_subscribe = AsyncMock(return_value=unsubscribe_mock)
    hass = MagicMock()
    entity = TerneoBinarySensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="heating",
        name="Heating",
        device_class=None,
        topic_suffix="load"
    )
    entity.hass = hass

    await entity.async_added_to_hass()
    await entity.async_will_remove_from_hass()

    unsubscribe_mock.assert_called_once()


@pytest.mark.asyncio
async def test_binary_sensor_mqtt_message_handling() -> None:
    """Test MQTT message handling for binary sensors."""
    hass = MagicMock()
    entity = TerneoBinarySensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="heating",
        name="Heating",
        device_class=None,
        topic_suffix="load"
    )

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

    # Test heating on
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity.is_on is True
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test heating off
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity.is_on is False
    entity.async_write_ha_state.assert_called_once()