# Inspire Integration Services

The Inspire Home Automation integration exposes the following services for advanced control and scheduling. Use **Developer Tools → Services** to call them, or reference them in automations and scripts.

You need the **device_id** for each thermostat. Find it in **Settings → Devices & Services → Inspire → [your device]**; the device ID is in the device identifier or in the entity's attributes.

---

## inspire.schedule_heating_start

Schedule the heating to start at a specific date/time.

| Parameter   | Type   | Required | Description                                              |
|------------|--------|----------|----------------------------------------------------------|
| device_id  | string | Yes      | Inspire device ID                                        |
| datetime   | string | Yes      | Date/time for scheduled start (use format required by API, e.g. ISO) |

**Example:**

```yaml
service: inspire.schedule_heating_start
data:
  device_id: "12345"
  datetime: "2025-02-09T07:00:00"
```

---

## inspire.cancel_scheduled_start

Cancel a scheduled heating start.

| Parameter  | Type   | Required | Description       |
|-----------|--------|----------|-------------------|
| device_id | string | Yes      | Inspire device ID |

**Example:**

```yaml
service: inspire.cancel_scheduled_start
data:
  device_id: "12345"
```

---

## inspire.advance_program

Advance the thermostat to the next program period (e.g. skip to the next time slot).

| Parameter  | Type   | Required | Description       |
|-----------|--------|----------|-------------------|
| device_id | string | Yes      | Inspire device ID |

**Example:**

```yaml
service: inspire.advance_program
data:
  device_id: "12345"
```

---

## inspire.sync_device_time

Synchronize the device clock with a time value you provide.

| Parameter  | Type   | Required | Description                                |
|-----------|--------|----------|--------------------------------------------|
| device_id | string | Yes      | Inspire device ID                          |
| time      | string | Yes      | Time string (e.g. ISO or HH:MM as per API) |

**Example:**

```yaml
service: inspire.sync_device_time
data:
  device_id: "12345"
  time: "14:30"
```

---

## inspire.set_program_schedule

Configure a single program schedule slot (program number, day, period, time, and set point temperature).

| Parameter    | Type   | Required | Description                                      |
|-------------|--------|----------|--------------------------------------------------|
| device_id   | string | Yes      | Inspire device ID                                |
| program     | int    | Yes      | Program number: 1 or 2                            |
| day         | int    | Yes      | Day index (0–6; check API for exact day mapping)  |
| period      | int    | Yes      | Period index within the day (0-based)             |
| time        | string | Yes      | Time for this period (e.g. `"07:00"`)            |
| temperature | float  | Yes      | Set point in °C (10–30, 0.5 steps)               |

**Example:**

```yaml
service: inspire.set_program_schedule
data:
  device_id: "12345"
  program: 1
  day: 0
  period: 0
  time: "07:00"
  temperature: 21.0
```

---

## inspire.set_program_type

Set the program type on the device. The exact values depend on the Inspire API; use the value or code expected by the API.

| Parameter     | Type   | Required | Description                    |
|--------------|--------|----------|--------------------------------|
| device_id    | string | Yes      | Inspire device ID              |
| program_type | string | Yes      | Program type value/code        |

**Example:**

```yaml
service: inspire.set_program_type
data:
  device_id: "12345"
  program_type: "1"
```

---

## Using in Automations

Example: advance the program every weekday at 6:00 for a specific thermostat.

```yaml
alias: "Inspire advance program weekday"
trigger:
  - platform: time
    at: "06:00:00"
condition:
  - condition: time
    weekday:
      - mon
      - tue
      - wed
      - thu
      - fri
action:
  - service: inspire.advance_program
    data:
      device_id: "YOUR_DEVICE_ID"
```

Example: sync device time at 3:00 every night.

```yaml
alias: "Inspire sync device time"
trigger:
  - platform: time
    at: "03:00:00"
action:
  - service: inspire.sync_device_time
    data:
      device_id: "YOUR_DEVICE_ID"
      time: "{{ now().strftime('%H:%M') }}"
```

---

## Notes

- The Inspire API applies a rate limit (e.g. 1 second between requests). The integration enforces this; avoid calling these services in very tight loops.
- After calling a service that changes device state, the integration will request a coordinator refresh so entities update.
- If a device is offline, scheduling and other write operations may fail; check logs and connection status.
