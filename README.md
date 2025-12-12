# ha-terneo-mqtt

Home Assistant integration for Terneo thermostats using MQTT.

## Features

This integration provides the following entities for each configured Terneo device:

- **Climate Entity**: Control temperature, heating mode, and power state.
- **Sensor Entities**:
  - Floor temperature
  - Protection temperature
  - Load (current consumption)
  - Wi-Fi RSSI (HTTP enrichment)
  - Power consumption (HTTP enrichment)
  - Energy usage (HTTP enrichment)
  - Voltage (HTTP enrichment)
  - Current (HTTP enrichment)
- **Binary Sensor Entity**:
  - Heating state (on/off based on load)
- **Number Entity**:
  - Brightness (0-9 for display brightness)
- **Select Entity**:
  - Mode (schedule/manual)

## Installation

1. Copy the `custom_components/terneo_mqtt` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via the UI: Settings > Devices & Services > Add Integration > Terneo MQTT.

## Configuration

During setup, provide:
- Device configurations: Comma-separated list of `client_id:host:sn` (sn optional)
- MQTT broker details (host, port, credentials)
- Device prefix (default: "terneo")

Example: `terneo_ax_1:192.168.1.10:12345,terneo_ax_2:192.168.1.11`

### Optional HTTP Telemetry Enrichment

If host is provided for a device, additional sensors will be created automatically using HTTP API command `{"cmd":4}`.

### Optional HTTP Telemetry Enrichment

For additional sensors (power, energy, Wi-Fi RSSI, diagnostics), enable HTTP enrichment in options:
- Host/IP of the Terneo device
- Optional serial number (SN)
- Poll interval (default: 60 seconds)

This fetches extended telemetry via HTTP API command `{"cmd":4}`.

## MQTT Topics

The integration subscribes to and publishes on the following topics:

- `{prefix}/{client_id}/protTemp` - Protection temperature
- `{prefix}/{client_id}/floorTemp` - Floor temperature
- `{prefix}/{client_id}/setTemp` - Set temperature (commands)
- `{prefix}/{client_id}/load` - Load state
- `{prefix}/{client_id}/bright` - Display brightness
- `{prefix}/{client_id}/mode` - Operation mode (0=schedule, 1=manual)

## Running Tests

To run the test suite:

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
python -m pytest
```

## License

MIT
