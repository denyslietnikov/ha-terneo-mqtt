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

    # Test with valid data - should go to device_config
    result = await flow.async_step_user({
        "devices_config": "terneo_ax_1B0026",
        "topic_prefix": "terneo"
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "device_config"


@pytest.mark.asyncio
async def test_config_flow_full() -> None:
    """Test the full config flow with multiple devices."""
    hass = MagicMock()
    flow = TerneoMQTTConfigFlow()
    flow.hass = hass

    # Step 1: user
    result = await flow.async_step_user({
        "client_ids": "terneo_ax_1,terneo_ax_2",
        "topic_prefix": "terneo"
    })
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "device_config"

    # Step 2: device config for terneo_ax_1
    result = await flow.async_step_device_config({
        "host": "192.168.1.10",
        "sn": "12345"
    })
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "device_config"

    # Step 3: device config for terneo_ax_2
    result = await flow.async_step_device_config({
        "host": "",
        "sn": ""
    })
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "prefix": "terneo",
        "devices": [
            {"client_id": "terneo_ax_1", "host": "192.168.1.10", "sn": "12345"},
            {"client_id": "terneo_ax_2", "host": "", "sn": ""}
        ]
    }


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