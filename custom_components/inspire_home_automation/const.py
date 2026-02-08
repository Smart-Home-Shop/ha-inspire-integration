"""Constants for the Inspire integration."""

DOMAIN = "inspire_home_automation"

# Configuration
CONF_API_KEY = "api_key"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# API
API_BASE_URL = "https://www.inspirehomeautomation.co.uk/client/api1_4/api.php"

# Update interval
DEFAULT_SCAN_INTERVAL = 120  # seconds (2 minutes)

# Temperature constraints
MIN_TEMP = 10.0  # °C
MAX_TEMP = 30.0  # °C
TEMP_STEP = 0.5  # °C

# Function/mode values
FUNCTION_OFF = 1
FUNCTION_PROGRAM_1 = 2
FUNCTION_PROGRAM_2 = 3
FUNCTION_BOTH_PROGRAMS = 4
FUNCTION_ON = 5
FUNCTION_BOOST = 6

# Service names
SERVICE_SCHEDULE_HEATING_START = "schedule_heating_start"
SERVICE_CANCEL_SCHEDULED_START = "cancel_scheduled_start"
SERVICE_ADVANCE_PROGRAM = "advance_program"
SERVICE_SYNC_DEVICE_TIME = "sync_device_time"
SERVICE_SET_PROGRAM_SCHEDULE = "set_program_schedule"
SERVICE_SET_PROGRAM_TYPE = "set_program_type"

# Program schedule parameters
PROGRAM_MIN = 1
PROGRAM_MAX = 2
DAY_MIN = 0
DAY_MAX = 6
PERIOD_MIN = 0
