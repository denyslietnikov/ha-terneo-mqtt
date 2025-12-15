"""Test TerneoMQ sensor entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.get_value.return_value = None
    entity = TerneoSensor(
        hass=hass,
        coordinator=coordinator,
        sensor_type="floor_temp",
        name="Floor Temperature",
        device_class=None,
        state_class=None,
        unit_of_measurement="°C",
        model="AX",
    )

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity.unique_id == "terneo_ax_1B0026_floor_temp"
    assert entity.name == "Terneo terneo_ax_1B0026 Floor Temperature"


@pytest.mark.asyncio
@patch("custom_components.terneo.base_entity.async_dispatcher_connect")
async def test_sensor_async_added_to_hass(mock_dispatcher) -> None:
    """Test dispatcher connection when entity is added."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.get_value.return_value = None
    entity = TerneoSensor(
        hass=hass,
        coordinator=coordinator,
        sensor_type="floorTemp",
        name="Floor Temperature",
        device_class=None,
        state_class=None,
        unit_of_measurement="°C",
        model="AX",
    )
    entity.hass = hass

    await entity.async_added_to_hass()

    mock_dispatcher.assert_called_once_with(
        hass, "terneo_terneo_ax_1B0026_update", entity._handle_coordinator_update
    )


@pytest.mark.asyncio
@patch("custom_components.terneo.base_entity.async_dispatcher_connect")
async def test_sensor_async_will_remove_from_hass(mock_dispatcher) -> None:
    """Test dispatcher disconnection when entity is removed."""
    unsubscribe_mock = MagicMock()
    mock_dispatcher.return_value = unsubscribe_mock
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.get_value.return_value = None
    entity = TerneoSensor(
        hass=hass,
        coordinator=coordinator,
        sensor_type="floorTemp",
        name="Floor Temperature",
        device_class=None,
        state_class=None,
        unit_of_measurement="°C",
        model="AX",
    )
    entity.hass = hass

    await entity.async_added_to_hass()
    await entity.async_will_remove_from_hass()

    unsubscribe_mock.assert_called_once()


@pytest.mark.asyncio
async def test_sensor_mqtt_message_handling() -> None:
    """Test MQTT message handling."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.get_value.return_value = None
    entity = TerneoSensor(
        hass=hass,
        coordinator=coordinator,
        sensor_type="floorTemp",
        name="Floor Temperature",
        device_class=None,
        state_class=None,
        unit_of_measurement="°C",
        model="AX",
    )

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Test temperature update
    entity._handle_coordinator_update("floorTemp", 25.5)

    assert entity._attr_native_value == 25.5
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test load update (integer)
    load_entity = TerneoSensor(
        hass=hass,
        coordinator=coordinator,
        sensor_type="load",
        name="Load",
        device_class=None,
        state_class=None,
        unit_of_measurement=None,
        model="AX",
    )
    load_entity.async_write_ha_state = MagicMock()

    load_entity._handle_coordinator_update("load", 1)

    assert load_entity._attr_native_value == 1
    load_entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
@patch("custom_components.terneo.sensor.TerneoCoordinator")
async def test_sensor_async_setup_entry(mock_coordinator_class) -> None:
    """Test sensor platform setup."""
    mock_coordinator = MagicMock()
    mock_coordinator.client_id = "test_device"
    mock_coordinator.get_value.return_value = None
    mock_coordinator_class.return_value = mock_coordinator
    mock_coordinator.async_setup = AsyncMock()

    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.data = {"devices": [{"client_id": "test_device"}]}
    config_entry.options = {"topic_prefix": "terneo", "model": "AX"}

    async_add_entities = MagicMock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 3  # floor_temp, prot_temp, state_sensor
    assert sum(1 for e in entities if isinstance(e, TerneoSensor)) == 2
    assert sum(1 for e in entities if isinstance(e, TerneoStateSensor)) == 1


@pytest.mark.asyncio
async def test_state_sensor_entity_creation() -> None:
    """Test state sensor entity initialization."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.get_value.return_value = None
    entity = TerneoStateSensor(hass=hass, coordinator=coordinator, model="AX")

    assert entity._client_id == "terneo_ax_1B0026"
    assert entity.unique_id == "terneo_ax_1B0026_state"
    assert entity.name == "Terneo terneo_ax_1B0026 State"


@pytest.mark.asyncio
async def test_state_sensor_mqtt_message_handling() -> None:
    """Test MQTT message handling for state sensor."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    # Mock get_value to return appropriate values
    coordinator.get_value.side_effect = lambda key: {
        "powerOff": 1,
        "load": 0,
        "mode": None,
    }.get(key)
    entity = TerneoStateSensor(hass=hass, coordinator=coordinator, model="AX")
    entity.hass = hass

    # Mock write_ha_state
    entity.async_write_ha_state = MagicMock()

    # Test powerOff update (off)
    entity._handle_coordinator_update("powerOff", 1)

    assert entity._attr_native_value == "Off"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test powerOff update (on), load=0 -> Idle
    coordinator.get_value.side_effect = lambda key: {
        "powerOff": 0,
        "load": 0,
        "mode": None,
    }.get(key)
    entity._handle_coordinator_update("powerOff", 0)

    assert entity._attr_native_value == "Idle"
    entity.async_write_ha_state.assert_called_once()

    # Reset mock
    entity.async_write_ha_state.reset_mock()

    # Test load update (heating on) -> Heat
    coordinator.get_value.side_effect = lambda key: {
        "powerOff": 0,
        "load": 1,
        "mode": None,
    }.get(key)
    entity._handle_coordinator_update("load", 1)

    assert entity._attr_native_value == "Heat"


@pytest.mark.asyncio
@patch("custom_components.terneo.sensor.TerneoCoordinator")
async def test_sensor_async_setup_entry_with_energy(mock_coordinator_class) -> None:
    """Test sensor platform setup with energy sensors enabled."""
    mock_coordinator = MagicMock()
    mock_coordinator.client_id = "test_device"
    mock_coordinator.get_value.return_value = None
    mock_coordinator_class.return_value = mock_coordinator
    mock_coordinator.async_setup = AsyncMock()

    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.data = {"devices": [{"client_id": "test_device"}]}
    config_entry.options = {
        "topic_prefix": "terneo",
        "rated_power_w": 1500,
        "model": "AX",
    }

    async_add_entities = MagicMock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entities were added
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 5  # 3 basic + 2 energy sensors per device
    assert sum(1 for e in entities if isinstance(e, TerneoSensor)) == 2
    assert sum(1 for e in entities if isinstance(e, TerneoPowerSensor)) == 1
    assert sum(1 for e in entities if isinstance(e, TerneoEnergySensor)) == 1
    assert sum(1 for e in entities if isinstance(e, TerneoStateSensor)) == 1


@pytest.mark.asyncio
async def test_power_sensor() -> None:
    """Test power sensor functionality."""
    hass = MagicMock()
    hass.config.components = ["sensor"]
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.get_value.return_value = None

    entity = TerneoPowerSensor(
        hass=hass,
        coordinator=coordinator,
        rated_power_w=1500,
        model="AX",
    )
    entity.hass = hass
    entity.platform = MagicMock()
    entity.async_write_ha_state = MagicMock()

    await entity.async_added_to_hass()

    # Test load=0 (no power)
    entity._handle_coordinator_update("load", 0)
    assert entity._attr_native_value == 0
    entity.async_write_ha_state.assert_called()

    # Test load=1 (full power)
    entity._handle_coordinator_update("load", 1)
    assert entity._attr_native_value == 1500
    assert entity.async_write_ha_state.call_count == 2


@pytest.mark.asyncio
async def test_energy_sensor() -> None:
    """Test energy sensor functionality."""
    hass = MagicMock()
    hass.config.components = ["sensor"]
    coordinator = MagicMock()
    coordinator.client_id = "terneo_ax_1B0026"
    coordinator.get_value.return_value = None

    entity = TerneoEnergySensor(
        hass=hass,
        coordinator=coordinator,
        rated_power_w=1500,
        model="AX",
    )
    entity.hass = hass
    entity.platform = MagicMock()
    entity.async_write_ha_state = MagicMock()
    entity.async_get_last_state = AsyncMock(return_value=None)

    await entity.async_added_to_hass()

    # Initial state
    assert entity._attr_native_value == 0.0

    # Simulate 1 hour of heating (load=1)
    # First update to initialize
    entity._handle_load_update("load", 1)

    # Simulate time passing (1 hour = 3600 seconds)
    entity._last_update = entity._last_update - 3600

    # Second update after 1 hour
    entity._handle_load_update("load", 1)

    # Should have consumed 1.5 kWh (1500W * 1h = 1.5 kWh)
    assert abs(entity._attr_native_value - 1.5) < 0.01
    assert entity.async_write_ha_state.call_count == 2
