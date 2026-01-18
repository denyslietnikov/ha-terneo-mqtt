"""Tests for integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.terneo import async_setup_entry
from custom_components.terneo.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry_resets_status_on_start() -> None:
    """Test setup sends reset commands when option is enabled."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.data = {"devices": [{"client_id": "terneo_ax_1B0026"}]}
    config_entry.options = {
        "topic_prefix": "terneo",
        "supports_air_temp": True,
        "reset_status_on_start": True,
    }

    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.async_setup = AsyncMock()
    coordinator.publish_command = AsyncMock()
    coordinator.set_cached_value = MagicMock()

    with patch("custom_components.terneo.TerneoCoordinator", return_value=coordinator):
        await async_setup_entry(hass, config_entry)

    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]
    coordinator.async_setup.assert_awaited_once()
    coordinator.set_cached_value.assert_any_call("powerOff", 1)
    coordinator.set_cached_value.assert_any_call("setTemp", 18.0)
    coordinator.publish_command.assert_any_await("powerOff", "1")
    coordinator.publish_command.assert_any_await("setTemp", "18")
