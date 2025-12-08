"""Test Terneo MQTT sensor entities."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.core import HomeAssistant

from custom_components.terneo_mqtt.sensor import TerneoSensor


@pytest.mark.asyncio
async def test_sensor_entity_creation() -> None:
    """Test sensor entity initialization."""
    hass = MagicMock()
    entity = TerneoSensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="floor_temp",
        name="Floor Temperature",
        device_class=None,
        state_class=None,
        unit_of_measurement="°C",
        topic_suffix="floorTemp"
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._topic == "terneo/terneo_ax_1B0026/floorTemp"
    assert entity.unique_id == "terneo_ax_1B0026_floor_temp"
    assert entity.name == "Terneo terneo_ax_1B0026 Floor Temperature"


@pytest.mark.asyncio
async def test_sensor_mqtt_message_handling() -> None:
    """Test MQTT message handling."""
    hass = MagicMock()
    entity = TerneoSensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="floor_temp",
        name="Floor Temperature",
        device_class=None,
        state_class=None,
        unit_of_measurement="°C",
        topic_suffix="floorTemp"
    )

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

    # Test temperature message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="25.5",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity.native_value == 25.5
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test load message (integer)
    load_entity = TerneoSensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="load",
        name="Load",
        device_class=None,
        state_class=None,
        unit_of_measurement=None,
        topic_suffix="load"
    )
    load_entity.async_write_ha_state = AsyncMock()

    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890
    )
    load_entity._handle_message(msg)

    assert load_entity.native_value == 1
    load_entity.async_write_ha_state.assert_called_once()