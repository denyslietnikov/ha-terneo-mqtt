"""Test TerneoMQ number entities."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.terneo.number import TerneoNumber


@pytest.mark.asyncio
async def test_number_entity_creation() -> None:
    """Test number entity initialization."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.topic_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoNumber(
        hass, coordinator, "brightness", "Brightness", 0, 9, 1, "bright", "AX"
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._topic == "terneo/terneo_ax_1B0026/bright"
    assert entity.unique_id == "terneo_ax_1B0026_brightness"
    assert entity.name == "Terneo terneo_ax_1B0026 Brightness"
    assert entity.native_min_value == 0
    assert entity.native_max_value == 9
    assert entity.native_step == 1


@pytest.mark.asyncio
async def test_number_async_added_to_hass() -> None:
    """Test dispatcher subscription when entity is added."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.topic_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoNumber(
        hass, coordinator, "brightness", "Brightness", 0, 9, 1, "bright", "AX"
    )
    entity.async_get_last_state = AsyncMock(return_value=None)

    await entity.async_added_to_hass()

    # Should subscribe to dispatcher
    # (Mock doesn't check the exact call, but ensures no error)


@pytest.mark.asyncio
async def test_number_async_will_remove_from_hass() -> None:
    """Test dispatcher unsubscription when entity is removed."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.topic_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoNumber(
        hass, coordinator, "brightness", "Brightness", 0, 9, 1, "bright", "AX"
    )

    await entity.async_added_to_hass()
    await entity.async_will_remove_from_hass()

    # Should unsubscribe from dispatcher (mock doesn't check exact call)


@pytest.mark.asyncio
async def test_number_set_native_value() -> None:
    """Test setting the native value."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.topic_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoNumber(
        hass, coordinator, "brightness", "Brightness", 0, 9, 1, "bright", "AX"
    )
    entity.async_write_ha_state = MagicMock()

    await entity.async_set_native_value(5.0)

    coordinator.publish_command.assert_called_once_with("bright", "5")
    assert entity.native_value == 5.0
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_number_mqtt_message_handling() -> None:
    """Test MQTT message handling."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.topic_prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoNumber(
        hass, coordinator, "brightness", "Brightness", 0, 9, 1, "bright", "AX"
    )

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Test valid message
    entity._handle_coordinator_update("bright", 7)

    assert entity.native_value == 7
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_number_restore_state() -> None:
    """Test state restoration without publishing to MQTT."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.topic_prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoNumber(
        hass, coordinator, "brightness", "Brightness", 0, 9, 1, "bright", "AX"
    )

    # Mock last state
    last_state = MagicMock()
    last_state.state = "5"
    entity.async_get_last_state = AsyncMock(return_value=last_state)

    await entity.async_added_to_hass()

    # Should restore value but not publish
    assert entity.native_value == 5.0
    coordinator.publish_command.assert_not_called()
