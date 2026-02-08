"""Constants for the Inspire integration."""

DOMAIN = "inspire"

# Configuration
CONF_API_KEY = "api_key"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# API
API_BASE_URL = "https://www.inspirehomeautomation.co.uk/client/api1_4/api.php"

# Update interval
DEFAULT_SCAN_INTERVAL = 60  # seconds

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
