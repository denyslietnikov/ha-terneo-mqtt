"""Test TerneoMQ binary sensor entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.terneo.binary_sensor import TerneoBinarySensor, async_setup_entry
from custom_components.terneo.const import DOMAIN


@pytest.mark.asyncio
async def test_binary_sensor_entity_creation() -> None:
    """Test binary sensor entity initialization."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    entity = TerneoBinarySensor(
        hass=hass,
        coordinator=coordinator,
        sensor_type="heating",
        name="Heating",
        device_class=BinarySensorDeviceClass.HEAT,
        model="AX",
        topic_suffix="load",
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity.unique_id == "terneo_ax_1B0026_heating"
    assert entity.name == "Terneo terneo_ax_1B0026 Heating"
    assert entity.device_class == BinarySensorDeviceClass.HEAT
    assert entity._attr_is_on is None


@pytest.mark.asyncio
async def test_binary_sensor_update_value() -> None:
    """Test binary sensor value update."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    entity = TerneoBinarySensor(
        hass=hass,
        coordinator=coordinator,
        sensor_type="heating",
        name="Heating",
        device_class=BinarySensorDeviceClass.HEAT,
        model="AX",
        topic_suffix="load",
    )

    # Test on
    entity.update_value(1)
    assert entity.is_on is True

    # Test off
    entity.update_value(0)
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_binary_sensor_parse_value() -> None:
    """Test binary sensor value parsing."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.telemetry_prefix = "terneo"
    coordinator.command_prefix = "terneo"
    entity = TerneoBinarySensor(
        hass=hass,
        coordinator=coordinator,
        sensor_type="heating",
        name="Heating",
        device_class=BinarySensorDeviceClass.HEAT,
        model="AX",
        topic_suffix="load",
    )

    assert entity.parse_value("1") == 1
    assert entity.parse_value("0") == 0


@pytest.mark.asyncio
async def test_async_setup_entry() -> None:
    """Test async setup entry for binary sensor."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.data = {"devices": [{"client_id": "terneo_ax_1B0026"}]}
    config_entry.options = {
        "topic_prefix": "terneo",
        "supports_air_temp": True,
        "model": "AX",
    }
    async_add_entities = AsyncMock()

    mock_coordinator = MagicMock()
    mock_coordinator.client_id = "terneo_ax_1B0026"
    mock_coordinator.telemetry_prefix = "terneo"
    mock_coordinator.command_prefix = "terneo"

    # Mock hass.data to return the coordinator
    hass.data = {
        DOMAIN: {config_entry.entry_id: {"terneo_ax_1B0026": mock_coordinator}}
    }

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], TerneoBinarySensor)
    assert entities[0]._sensor_type == "heating"
