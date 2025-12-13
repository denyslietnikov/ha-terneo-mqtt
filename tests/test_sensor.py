"""Test TerneoMQ sensor entities."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.core import HomeAssistant

from custom_components.terneo_mqtt.sensor import TerneoSensor, TerneoModeSensor, async_setup_entry


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
@patch('custom_components.terneo_mqtt.sensor.mqtt')
async def test_sensor_async_added_to_hass(mock_mqtt) -> None:
    """Test MQTT subscription when entity is added."""
    unsubscribe_mock = MagicMock()
    mock_mqtt.async_subscribe = AsyncMock(return_value=unsubscribe_mock)
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
    entity.hass = hass

    await entity.async_added_to_hass()

    mock_mqtt.async_subscribe.assert_called_once_with(hass, entity._topic, entity._handle_message, qos=0)
    assert entity._unsubscribe == unsubscribe_mock


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.sensor.mqtt')
async def test_sensor_async_will_remove_from_hass(mock_mqtt) -> None:
    """Test MQTT unsubscription when entity is removed."""
    unsubscribe_mock = MagicMock()
    mock_mqtt.async_subscribe = AsyncMock(return_value=unsubscribe_mock)
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
    entity.hass = hass

    await entity.async_added_to_hass()
    await entity.async_will_remove_from_hass()

    unsubscribe_mock.assert_called_once()


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


@pytest.mark.asyncio
async def test_sensor_async_setup_entry() -> None:
    """Test sensor platform setup."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.data = {"devices": [{"client_id": "test_device"}]}
    config_entry.options = {"topic_prefix": "terneo"}
    
    async_add_entities = AsyncMock()
    
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    # Verify entities were added
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 4  # 4 sensor entities per device (floor_temp, prot_temp, load, mode)
    assert sum(1 for e in entities if isinstance(e, TerneoSensor)) == 3
    assert sum(1 for e in entities if hasattr(e, '_update_mode')) == 1  # TerneoModeSensor


@pytest.mark.asyncio
async def test_mode_sensor_entity_creation() -> None:
    """Test mode sensor entity initialization."""
    entity = TerneoModeSensor(client_id="terneo_ax_1B0026", prefix="terneo")

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity.unique_id == "terneo_ax_1B0026_mode"
    assert entity.name == "Terneo terneo_ax_1B0026 Mode"


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.sensor.mqtt')
async def test_mode_sensor_mqtt_message_handling(mock_mqtt) -> None:
    """Test MQTT message handling for mode sensor."""
    hass = MagicMock()
    entity = TerneoModeSensor(client_id="terneo_ax_1B0026", prefix="terneo")
    entity.hass = hass

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

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

    assert entity.native_value == "Off"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test powerOff message (on), load=0 -> Idle
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/powerOff",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/powerOff",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity.native_value == "Idle"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test load message (heating on) -> Heat
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity.native_value == "Heat"
    entity.async_write_ha_state.assert_called_once()