"""Test Terneo MQTT select entities."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.core import HomeAssistant

from custom_components.terneo_mqtt.select import TerneoSelect


@pytest.mark.asyncio
async def test_select_entity_creation() -> None:
    """Test select entity initialization."""
    hass = MagicMock()
    entity = TerneoSelect(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="mode",
        name="Mode",
        options=["schedule", "manual"],
        topic_suffix="mode"
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._topic == "terneo/terneo_ax_1B0026/mode"
    assert entity.unique_id == "terneo_ax_1B0026_mode"
    assert entity.name == "Terneo terneo_ax_1B0026 Mode"
    assert entity.options == ["schedule", "manual"]


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.select.mqtt')
async def test_select_async_added_to_hass(mock_mqtt) -> None:
    """Test MQTT subscription when entity is added."""
    mock_mqtt.async_subscribe = AsyncMock()
    hass = MagicMock()
    entity = TerneoSelect(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="mode",
        name="Mode",
        options=["schedule", "manual"],
        topic_suffix="mode"
    )
    entity.hass = hass

    await entity.async_added_to_hass()

    mock_mqtt.async_subscribe.assert_called_once_with(hass, entity._topic, entity._handle_message, qos=0)


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.select.mqtt')
async def test_select_async_will_remove_from_hass(mock_mqtt) -> None:
    """Test MQTT unsubscription when entity is removed."""
    mock_mqtt.async_unsubscribe = AsyncMock()
    hass = MagicMock()
    entity = TerneoSelect(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="mode",
        name="Mode",
        options=["schedule", "manual"],
        topic_suffix="mode"
    )
    entity.hass = hass

    await entity.async_will_remove_from_hass()

    mock_mqtt.async_unsubscribe.assert_called_once_with(hass, entity._topic)


@pytest.mark.asyncio
@patch('custom_components.terneo_mqtt.select.mqtt')
async def test_select_async_select_option(mock_mqtt) -> None:
    """Test selecting an option."""
    mock_mqtt.async_publish = AsyncMock()
    hass = MagicMock()
    entity = TerneoSelect(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="mode",
        name="Mode",
        options=["schedule", "manual"],
        topic_suffix="mode"
    )
    entity.hass = hass
    entity.async_write_ha_state = AsyncMock()

    await entity.async_select_option("manual")

    mock_mqtt.async_publish.assert_called_once_with(hass, entity._command_topic, "1", qos=0)
    assert entity.current_option == "manual"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_select_mqtt_message_handling() -> None:
    """Test MQTT message handling."""
    hass = MagicMock()
    entity = TerneoSelect(
        client_id="terneo_ax_1B0026",
        prefix="terneo",
        sensor_type="mode",
        name="Mode",
        options=["schedule", "manual"],
        topic_suffix="mode"
    )

    # Mock write_ha_state
    entity.async_write_ha_state = AsyncMock()

    # Test schedule message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/mode",
        payload="0",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/mode",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity.current_option == "schedule"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test manual message
    msg = ReceiveMessage(
        topic="terneo/terneo_ax_1B0026/mode",
        payload="1",
        qos=0,
        retain=False,
        subscribed_topic="terneo/terneo_ax_1B0026/mode",
        timestamp=1234567890
    )
    entity._handle_message(msg)

    assert entity.current_option == "manual"
    entity.async_write_ha_state.assert_called_once()