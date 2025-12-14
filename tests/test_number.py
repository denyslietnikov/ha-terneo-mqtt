"""Test TerneoMQ number entities."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.mqtt import ReceiveMessage

from custom_components.terneo.number import TerneoNumber


@pytest.mark.asyncio
async def test_number_entity_creation() -> None:
    """Test number entity initialization."""
    _ = MagicMock()
    entity = TerneoNumber(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="brightness",
        name="Brightness",
        min_value=0,
        max_value=9,
        step=1,
        topic_suffix="bright",
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._topic == "terneo/terneo_ax_1B0026/bright"
    assert entity.unique_id == "terneo_ax_1B0026_brightness"
    assert entity.name == "Terneo terneo_ax_1B0026 Brightness"
    assert entity.native_min_value == 0
    assert entity.native_max_value == 9
    assert entity.native_step == 1


@pytest.mark.asyncio
@patch("custom_components.terneo.number.mqtt")
async def test_number_async_added_to_hass(mock_mqtt) -> None:
    """Test MQTT subscription when entity is added."""
    unsubscribe_mock = MagicMock()
    mock_mqtt.async_subscribe = AsyncMock(return_value=unsubscribe_mock)
    hass = MagicMock()
    entity = TerneoNumber(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="brightness",
        name="Brightness",
        min_value=0,
        max_value=9,
        step=1,
        topic_suffix="bright",
    )
    entity.hass = hass

    # Mock async_get_last_state to return None
    entity.async_get_last_state = AsyncMock(return_value=None)

    await entity.async_added_to_hass()

    mock_mqtt.async_subscribe.assert_called_once_with(
        hass, entity._topic, entity._handle_message, qos=0
    )
    assert entity._unsubscribe == unsubscribe_mock


@pytest.mark.asyncio
@patch("custom_components.terneo.number.mqtt")
async def test_number_async_will_remove_from_hass(mock_mqtt) -> None:
    """Test MQTT unsubscription when entity is removed."""
    unsubscribe_mock = MagicMock()
    mock_mqtt.async_subscribe = AsyncMock(return_value=unsubscribe_mock)
    hass = MagicMock()
    entity = TerneoNumber(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="brightness",
        name="Brightness",
        min_value=0,
        max_value=9,
        step=1,
        topic_suffix="bright",
    )
    entity.hass = hass

    await entity.async_added_to_hass()
    await entity.async_will_remove_from_hass()

    unsubscribe_mock.assert_called_once()


@pytest.mark.asyncio
@patch("homeassistant.components.mqtt.async_publish")
async def test_number_set_native_value(mock_async_publish) -> None:
    """Test setting the native value."""
    mock_async_publish.return_value = None
    hass = MagicMock()
    entity = TerneoNumber(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="brightness",
        name="Brightness",
        min_value=0,
        max_value=9,
        step=1,
        topic_suffix="bright",
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    await entity.async_set_native_value(5.0)

    mock_async_publish.assert_called_once_with(
        hass, entity._command_topic, "5", qos=0, retain=False
    )
    assert entity.native_value == 5.0
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_number_mqtt_message_handling() -> None:
    """Test MQTT message handling."""
    _ = MagicMock()
    entity = TerneoNumber(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="brightness",
        name="Brightness",
        min_value=0,
        max_value=9,
        step=1,
        topic_suffix="bright",
    )

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Test valid message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/bright",
        payload="7",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/bright",
        timestamp=1234567890,
    )
    entity._handle_message(msg)

    assert entity.native_value == 7
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch("homeassistant.components.mqtt.async_publish")
async def test_number_restore_state(mock_async_publish) -> None:
    """Test state restoration without publishing to MQTT."""
    mock_async_publish.return_value = None
    mock_subscribe = AsyncMock()
    with patch(
        "homeassistant.components.mqtt.async_subscribe", return_value=mock_subscribe
    ):
        hass = MagicMock()
        entity = TerneoNumber(
            client_id="terneo_ax_1B0026",
            prefix="terneo",
            sensor_type="brightness",
            name="Brightness",
            min_value=0,
            max_value=9,
            step=1,
            topic_suffix="bright",
        )
        entity.hass = hass

        # Mock last state
        last_state = MagicMock()
        last_state.state = "5"
        entity.async_get_last_state = AsyncMock(return_value=last_state)

        await entity.async_added_to_hass()

        # Should restore value but not publish
        assert entity.native_value == 5.0
        mock_async_publish.assert_not_called()
