# ha-terneo-mqtt

Home Assistant integration for Terneo thermostats using MQTT protocol for local control without cloud dependency.

## Features

This integration provides the following entities for each configured Terneo device:

- **Climate Entity**: Control temperature, heating mode (HEAT/AUTO/OFF), and power state.
- **Sensor Entities**:
  - Floor temperature
  - Protection temperature
  - Mode (Off/Idle/Heat based on device state)
  - Power (current power consumption in watts, requires rated power setting)
  - Energy (accumulated energy consumption in kWh, requires rated power setting)
- **Binary Sensor Entity**:
  - Heating (on/off indicator)
- **Number Entity**:
  - Brightness (0-9 for display brightness)
- **Select Entity**:
  - Mode (schedule/manual)

## Testing

This integration has been tested with Terneo AX model running firmware version 2.4 (Owl 3).

## Installation

1. Copy the `custom_components/terneo` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via the UI: Settings > Devices & Services > Add Integration > TerneoMQ.

## Configuration

During setup:
1. Provide comma-separated list of MQTT Client IDs (e.g., `terneo_ax_1С0056,terneo_ax_057019`)
2. Device prefix (default: "terneo")
3. Thermostat model (AX or SX)
4. Rated power of heating element in watts (0 = disabled)
### Options

After setup, you can configure additional options:
- **Topic prefix**: MQTT topic prefix used by devices
- **Model**: Thermostat model (AX or SX)
- **Rated power (W)**: Rated power of the heating element in watts. When set above 0, enables power and energy sensors for HA Energy dashboard integration. Set to 0 to disable energy monitoring.
## MQTT Topics

The integration subscribes to and publishes on the following topics:

- `{prefix}/{client_id}/setTemp` - Target temperature (commands)
- `{prefix}/{client_id}/floorTemp` - Floor temperature
- `{prefix}/{client_id}/protTemp` - Protection temperature
- `{prefix}/{client_id}/load` - Load state (0=idle, 1=heating)
- `{prefix}/{client_id}/powerOff` - Power state (0=on, 1=off)
- `{prefix}/{client_id}/mode` - Operation mode (0=auto/schedule, 1=manual)
- `{prefix}/{client_id}/bright` - Display brightness
- `{prefix}/{client_id}/airTemp` - Current air temperature (optional)

## HVAC Mode Logic

The climate entity intelligently manages HVAC modes:
- **HEAT**: Manual heating mode or when device is actively heating (load=1)
- **AUTO**: Automatic/schedule mode when not actively heating
- **OFF**: Device is powered off

When the device starts heating (load changes to 1), the mode automatically switches to HEAT to accurately reflect the current state, regardless of the configured mode.

## MQTT Broker Configuration

This integration requires MQTT broker to be configured in Home Assistant. The integration uses the following MQTT settings:

- **QoS**: 0 (At most once delivery)
- **Retain**: Commands are sent without retain flag to prevent command replay on device reconnection
- **Keep Alive**: Use default HA MQTT settings (60 seconds recommended)
- **Clean Session**: Enabled

Ensure your MQTT broker is properly configured and accessible from Home Assistant.
