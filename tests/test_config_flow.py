"""Test Terneo MQTT config flow."""
import pytest
from unittest.mock import MagicMock
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.terneo_mqtt import DOMAIN
from custom_components.terneo_mqtt.config_flow import TerneoMQTTConfigFlow, TerneoMQTTOptionsFlow


@pytest.mark.asyncio
async def test_config_flow_user() -> None:
    """Test the user config flow."""
    hass = MagicMock()
    flow = TerneoMQTTConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test with valid data
    result = await flow.async_step_user({
        "client_ids": "terneo_ax_1B0026",
        "topic_prefix": "terneo"
    })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Terneo MQTT"
    assert result["data"] == {
        "prefix": "terneo",
        "devices": [{"client_id": "terneo_ax_1B0026"}]
    }


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_config_flow_user_multiple_devices() -> None:
    """Test the user config flow with multiple devices."""
    hass = MagicMock()
    flow = TerneoMQTTConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user({
        "client_ids": "terneo_ax_1B0026,terneo_ax_058009",
        "topic_prefix": "terneo"
    })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["prefix"] == "terneo"
    assert result["data"]["devices"] == [
        {"client_id": "terneo_ax_1B0026"},
        {"client_id": "terneo_ax_058009"}
    ]


@pytest.mark.asyncio
async def test_options_flow() -> None:
    """Test the options flow."""
    hass = MagicMock()
    config_entry = MagicMock(spec=config_entries.ConfigEntry)
    config_entry.entry_id = "test_entry_id"
    config_entry.options = {}
    hass.config_entries.async_get_known_entry.return_value = config_entry
    flow = TerneoMQTTOptionsFlow(config_entry)
    flow.handler = "test_entry_id"  # Ensure handler is set
    flow.hass = hass

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Test with valid data
    result = await flow.async_step_init({
        "topic_prefix": "new_terneo"
    })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {"topic_prefix": "new_terneo"}