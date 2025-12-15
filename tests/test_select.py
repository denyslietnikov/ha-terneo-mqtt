"""Test TerneoMQ select entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.terneo.select import TerneoSelect


@pytest.mark.asyncio
async def test_select_entity_creation() -> None:
    """Test select entity initialization."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoSelect(
        hass,
        coordinator,
        "mode",
        "Mode",
        ["schedule", "manual", "away", "temporary"],
        "mode",
        "AX",
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity._topic_suffix == "mode"
    assert entity.unique_id == "terneo_ax_1B0026_mode"
    assert entity.name == "Terneo terneo_ax_1B0026 Mode"
    assert entity.options == ["schedule", "manual", "away", "temporary"]


@pytest.mark.asyncio
async def test_select_async_select_option() -> None:
    """Test selecting an option."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.prefix = "terneo"
    coordinator.supports_air_temp = True
    coordinator.publish_command = AsyncMock()
    entity = TerneoSelect(
        hass,
        coordinator,
        "mode",
        "Mode",
        ["schedule", "manual", "away", "temporary"],
        "mode",
        "AX",
    )
    entity.async_write_ha_state = MagicMock()

    # Test manual
    await entity.async_select_option("manual")
    coordinator.publish_command.assert_called_once_with("mode", "3")
    assert entity.current_option == "manual"
    entity.async_write_ha_state.assert_called_once()

    # Reset mocks
    coordinator.publish_command.reset_mock()
    entity.async_write_ha_state.reset_mock()

    # Test schedule
    await entity.async_select_option("schedule")
    coordinator.publish_command.assert_called_once_with("mode", "0")
    assert entity.current_option == "schedule"
    entity.async_write_ha_state.assert_called_once()

    # Reset mocks
    coordinator.publish_command.reset_mock()
    entity.async_write_ha_state.reset_mock()

    # Test away
    await entity.async_select_option("away")
    coordinator.publish_command.assert_called_once_with("mode", "4")
    assert entity.current_option == "away"
    entity.async_write_ha_state.assert_called_once()

    # Reset mocks
    coordinator.publish_command.reset_mock()
    entity.async_write_ha_state.reset_mock()

    # Test temporary
    await entity.async_select_option("temporary")
    coordinator.publish_command.assert_called_once_with("mode", "5")
    assert entity.current_option == "temporary"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_select_coordinator_update_handling() -> None:
    """Test coordinator update handling."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.prefix = "terneo"
    coordinator.supports_air_temp = True
    entity = TerneoSelect(
        hass,
        coordinator,
        "mode",
        "Mode",
        ["schedule", "manual", "away", "temporary"],
        "mode",
        "AX",
    )

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Test schedule message
    entity._handle_coordinator_update("mode", "0")

    assert entity.current_option == "schedule"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test manual message
    entity._handle_coordinator_update("mode", "3")

    assert entity.current_option == "manual"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test away message
    entity._handle_coordinator_update("mode", "4")

    assert entity.current_option == "away"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test temporary message
    entity._handle_coordinator_update("mode", "5")

    assert entity.current_option == "temporary"
    entity.async_write_ha_state.assert_called_once()
