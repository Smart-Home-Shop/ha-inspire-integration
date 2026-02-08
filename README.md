# Inspire Home Automation Integration for Home Assistant

A custom integration for Home Assistant to control Inspire Home Automation smart thermostats.

## Features

- Control Inspire thermostats from Home Assistant
- Monitor current temperature and set points
- Set target temperatures
- Change heating modes (Off, Program 1, Program 2, Both, Manual, Boost)
- Preset modes: none, program1, program2, both, boost
- Connection status (binary sensor) and battery sensors
- Account summary sensors
- Real-time status updates via cloud polling
- Home Assistant services for scheduling and program configuration (see [SERVICES.md](SERVICES.md))

## Prerequisites

- Home Assistant 2023.1 or newer
- An active Inspire Home Automation account with registered thermostats
- Your Inspire API credentials (see below)

## Getting Your API Credentials

To use this integration, you need three pieces of information:

### 1. API Key

1. Log into the Inspire web portal at https://www.inspirehomeautomation.co.uk/client/
2. Navigate to the **Advanced** tab
3. Your **API Key** will be displayed on this page
4. Copy this key (it's a long alphanumeric string)

### 2. Username

This is the **email address** you use to log into the Inspire web portal.

### 3. Password

This is the **password** you use to log into the Inspire web portal.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/paul-ridgway/ha-inspire-integration`
6. Select category: "Integration"
7. Click "Add"
8. Find "Inspire Home Automation" in the integration list and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/inspire` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Inspire Home Automation"
4. Enter your credentials:
   - **API Key**: The key from the Advanced tab in the Inspire portal
   - **Username**: Your Inspire account email address
   - **Password**: Your Inspire account password
5. Click **Submit**

The integration will automatically discover all thermostats on your account.

## Supported Devices

This integration supports the following Inspire Home Automation devices:

- Wireless Room Thermostats
- Touch Thermostats
- WiFi Relay Modules
- All devices that support the Inspire API v1.4

## Entities Created

For each thermostat/device, the integration creates:

- **Climate Entity**: Control temperature, HVAC mode, and preset (program1, program2, both, boost). Also shows current temperature (no separate temperature sensor for thermostats to avoid duplicates.)
  - `climate.inspire_<device_name>`
- **Battery Sensor**: Battery status (OK/Low or voltage), when reported by the device
  - `sensor.inspire_<device_name>_battery`

At the account level:

- **Summary Sensors**: One sensor per scalar value returned by the API summary (e.g. device count, active count), under device "Inspire Account".

## Services

The integration exposes services for scheduling and program configuration. See **[SERVICES.md](SERVICES.md)** for full descriptions and examples:

- `inspire.schedule_heating_start` – Schedule heating to start at a given time
- `inspire.cancel_scheduled_start` – Cancel a scheduled start
- `inspire.advance_program` – Advance to the next program period
- `inspire.sync_device_time` – Sync the device clock
- `inspire.set_program_schedule` – Configure a program slot (program, day, period, time, temperature)
- `inspire.set_program_type` – Set program type on the device

Example (Developer Tools → Services):

```yaml
service: inspire.advance_program
data:
  device_id: "YOUR_DEVICE_ID"
```

## HVAC Modes and Presets

The integration maps Inspire functions to Home Assistant:

| Inspire Mode | HA HVAC Mode | Preset   |
|--------------|--------------|----------|
| Off          | Off          | none     |
| Program 1    | Auto         | program1 |
| Program 2    | Auto         | program2 |
| Both         | Auto         | both     |
| Manual/On    | Heat         | (none)   |
| Boost        | Heat         | boost    |

## Troubleshooting

### Authentication Errors

If you get "Invalid authentication credentials":

1. Verify you can log into https://www.inspirehomeautomation.co.uk/client/ with your username and password
2. Check that you've copied the API key correctly from the Advanced tab
3. Ensure there are no extra spaces before or after the credentials
4. The API key should be a long string of random letters and numbers

### No Devices Found

If setup completes but no devices appear:

1. Log into the Inspire web portal
2. Verify that your thermostats are registered and showing online
3. Check that your gateway is connected (green indicator)

### Connection Issues

If you see "Failed to connect":

1. Check your internet connection
2. Verify the Inspire service is online (try logging into the web portal)
3. Check Home Assistant logs for detailed error messages

### Enable Debug Logging

To see detailed logs, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.inspire: debug
```

Then restart Home Assistant and check the logs at **Settings** → **System** → **Logs**.

## API Rate Limiting

The Inspire API requires a minimum of 1 second between requests. This integration:

- Automatically enforces rate limiting
- Polls device status every 60 seconds by default
- Queues commands to avoid exceeding rate limits

## Known Limitations

- Temperature can only be set in 0.5°C increments
- Temperature range is limited to 10-30°C
- Changes may take up to 30 seconds to appear on the physical thermostat (this is an API limitation)
- The integration requires cloud connectivity (no local API available)

## Support

- Report issues: https://github.com/paul-ridgway/ha-inspire-integration/issues
- Inspire API documentation: https://www.inspirehomeautomation.co.uk/client/api1_4/api.php?action=help
- Inspire Support: https://www.inspirehomeautomation.co.uk/support

## License

This integration is provided as-is without warranty. Use at your own risk.

## Credits

Developed for use with Inspire Home Automation thermostats and the Inspire Cloud API.
