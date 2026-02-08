# Quick Setup Guide

## Getting Your API Credentials

### Step 1: Get Your API Key

1. Open your web browser and go to: **https://www.inspirehomeautomation.co.uk/client/**
2. Log in with your Inspire account credentials
3. Once logged in, click on the **"Advanced"** tab
4. You will see your **API Key** displayed on this page
5. Copy the entire API key (it's a long string of random characters)

### Step 2: Note Your Login Credentials

You'll also need:
- **Username**: The email address you use to log into the Inspire portal
- **Password**: The password you use to log into the Inspire portal

## Setting Up in Home Assistant

### Method 1: Via UI (Recommended)

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click the **+ Add Integration** button
3. Search for **"Inspire Home Automation"**
4. When prompted, enter:
   - **API Key**: Paste the key from the Advanced tab
   - **Username**: Your Inspire login email
   - **Password**: Your Inspire login password
5. Click **Submit**

The integration will connect to the Inspire API and automatically discover all your thermostats.

### Method 2: Testing with Python Script

Before setting up in Home Assistant, you can test your credentials:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   INSPIRE_API_KEY=your_actual_api_key_here
   INSPIRE_USERNAME=your_email@example.com
   INSPIRE_PASSWORD=your_actual_password
   ```

3. Run the test script:
   ```bash
   ./test_api.sh
   ```
   or
   ```bash
   python3 test_inspire_api.py
   ```

If the test succeeds, you'll see a list of all your devices and their current status.

## What Gets Created

After setup, for each thermostat you'll get:

- **Climate Entity**: `climate.inspire_home_automation_<device_name>`
  - Control temperature and heating mode
  - View current temperature
  
- **Temperature Sensor**: `sensor.inspire_home_automation_<device_name>_temperature`
  - Current room temperature
  
- **Connection Sensor**: `binary_sensor.inspire_home_automation_<device_name>_connection`
  - Shows if device is online

## Common Issues

### "Invalid authentication credentials"

- Double-check you can log into https://www.inspirehomeautomation.co.uk/client/ with your username/password
- Make sure the API key is copied correctly (no extra spaces)
- The API key is case-sensitive

### "No devices found"

- Log into the Inspire portal and verify your thermostats are registered
- Check that your gateway shows as online (green light)
- Ensure your devices are communicating with the gateway

### "Failed to connect"

- Check your internet connection
- Verify the Inspire service is available by trying to access the web portal
- Check Home Assistant logs for more details

## Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Report issues at: https://github.com/Smart-Home-Shop/ha-inspire-integration/issues
- Inspire Support: https://www.inspirehomeautomation.co.uk/support
