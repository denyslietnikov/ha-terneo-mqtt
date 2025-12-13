"""Test TerneoMQ sensor entities."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.mqtt import ReceiveMessage

from custom_components.terneo.sensor import (
    TerneoEnergySensor,
    TerneoPowerSensor,
    TerneoSensor,
    TerneoStateSensor,
    async_setup_entry,
)


@pytest.mark.asyncio
async def test_sensor_entity_creation() -> None:
    """Test sensor entity initialization."""
    _ = MagicMock()
    entity = TerneoSensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="floor_temp",
        name="Floor Temperature",
        device_class=None,
        state_class=None,
        unit_of_measurement="°C",
        topic_suffix="floorTemp",
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._topic == "terneo/terneo_ax_1B0026/floorTemp"
    assert entity.unique_id == "terneo_ax_1B0026_floor_temp"
    assert entity.name == "Terneo terneo_ax_1B0026 Floor Temperature"


@pytest.mark.asyncio
@patch("custom_components.terneo.sensor.mqtt")
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
        topic_suffix="floorTemp",
    )
    entity.hass = hass

    await entity.async_added_to_hass()

    mock_mqtt.async_subscribe.assert_called_once_with(
        hass, entity._topic, entity._handle_message, qos=0
    )
    assert entity._unsubscribe == unsubscribe_mock


@pytest.mark.asyncio
@patch("custom_components.terneo.sensor.mqtt")
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
        topic_suffix="floorTemp",
    )
    entity.hass = hass

    await entity.async_added_to_hass()
    await entity.async_will_remove_from_hass()

    unsubscribe_mock.assert_called_once()


@pytest.mark.asyncio
async def test_sensor_mqtt_message_handling() -> None:
    """Test MQTT message handling."""
    _ = MagicMock()
    entity = TerneoSensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="floor_temp",
        name="Floor Temperature",
        device_class=None,
        state_class=None,
        unit_of_measurement="°C",
        topic_suffix="floorTemp",
    )

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Test temperature message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/floorTemp",
        payload="25.5",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/floorTemp",
        timestamp=1234567890,
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
        topic_suffix="load",
    )
    load_entity.async_write_ha_state = MagicMock()

    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
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
    assert (
        len(entities) == 4
    )  # 4 sensor entities per device (floor_temp, prot_temp, load, mode)
    assert sum(1 for e in entities if isinstance(e, TerneoSensor)) == 3
    assert (
        sum(1 for e in entities if hasattr(e, "_update_mode")) == 1
    )  # TerneoModeSensor


@pytest.mark.asyncio
async def test_state_sensor_entity_creation() -> None:
    """Test state sensor entity initialization."""
    entity = TerneoStateSensor(client_id="terneo_ax_1B0026", prefix="terneo")

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity.unique_id == "terneo_ax_1B0026_state"
    assert entity.name == "Terneo terneo_ax_1B0026 State"


@pytest.mark.asyncio
@patch("custom_components.terneo.sensor.mqtt")
async def test_state_sensor_mqtt_message_handling(mock_mqtt) -> None:
    """Test MQTT message handling for state sensor."""
    hass = MagicMock()
    entity = TerneoStateSensor(client_id="terneo_ax_1B0026", prefix="terneo")
    entity.hass = hass

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

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
        timestamp=1234567890,
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
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity.native_value == "Heat"


@pytest.mark.asyncio
async def test_sensor_async_setup_entry_with_energy() -> None:
    """Test sensor platform setup with energy sensors enabled."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.data = {"devices": [{"client_id": "test_device"}]}
    config_entry.options = {"topic_prefix": "terneo", "rated_power_w": 1500}

    async_add_entities = AsyncMock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 6  # 4 basic + 2 energy sensors per device
    assert sum(1 for e in entities if isinstance(e, TerneoSensor)) == 3
    assert sum(1 for e in entities if isinstance(e, TerneoPowerSensor)) == 1
    assert sum(1 for e in entities if isinstance(e, TerneoEnergySensor)) == 1
    assert (
        sum(1 for e in entities if hasattr(e, "_update_mode")) == 1
    )  # TerneoModeSensor


@pytest.mark.asyncio
@patch("custom_components.terneo.sensor.mqtt")
async def test_power_sensor(mock_mqtt) -> None:
    """Test power sensor functionality."""
    unsubscribe_mock = MagicMock()
    mock_mqtt.async_subscribe = AsyncMock(return_value=unsubscribe_mock)
    hass = MagicMock()
    hass.config.components = ["sensor"]

    entity = TerneoPowerSensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        rated_power_w=1500,
    )
    entity.hass = hass
    entity.platform = MagicMock()
    entity.async_write_ha_state = MagicMock()

    await entity.async_added_to_hass()

    # Test load=0 (no power)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_load_message(msg)
    assert entity.native_value == 0
    entity.async_write_ha_state.assert_called()

    # Test load=1 (full power)
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_load_message(msg)
    assert entity.native_value == 1500
    assert entity.async_write_ha_state.call_count == 2


@pytest.mark.asyncio
@patch("custom_components.terneo.sensor.mqtt")
async def test_energy_sensor(mock_mqtt) -> None:
    """Test energy sensor functionality."""
    unsubscribe_mock = MagicMock()
    mock_mqtt.async_subscribe = AsyncMock(return_value=unsubscribe_mock)
    hass = MagicMock()
    hass.config.components = ["sensor"]

    entity = TerneoEnergySensor(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        rated_power_w=1500,
    )
    entity.hass = hass
    entity.platform = MagicMock()
    entity.async_write_ha_state = MagicMock()

    await entity.async_added_to_hass()

    # Initial state
    assert entity.native_value == 0.0

    # Simulate 1 hour of heating (load=1)
    # First message to initialize
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890,
    )
    entity._handle_load_message(msg)

    # Simulate time passing (1 hour = 3600 seconds)
    entity._last_update = entity._last_update - 3600

    # Second message after 1 hour
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/load",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/load",
        timestamp=1234567890 + 3600,
    )
    entity._handle_load_message(msg)

    # Should have consumed 1.5 kWh (1500W * 1h = 1.5 kWh)
    assert abs(entity.native_value - 1.5) < 0.01
    assert entity.async_write_ha_state.call_count == 2
