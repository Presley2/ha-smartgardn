"""Constants for the smartgardn_et0 integration."""

# Domain & Storage
DOMAIN = "smartgardn_et0"
STORAGE_KEY = "smartgardn_et0"
STORAGE_VERSION = 1
VERSION = "0.2.1"

# Event names
EVENT_ZONE_STARTED = "smartgardn_et0_zone_started"
EVENT_ZONE_FINISHED = "smartgardn_et0_zone_finished"
EVENT_FROST_LOCK = "smartgardn_et0_frost_lock"
EVENT_FROST_RELEASE = "smartgardn_et0_frost_release"
EVENT_CALC_DONE = "smartgardn_et0_calc_done"
EVENT_FALLBACK_ACTIVE = "smartgardn_et0_fallback_active"
EVENT_UNEXPECTED_STATE = "smartgardn_et0_unexpected_state"

# Service names
SERVICE_START_ZONE = "start_zone"
SERVICE_STOP_ZONE = "stop_zone"
SERVICE_STOP_ALL = "stop_all"
SERVICE_RECALCULATE = "recalculate_now"
SERVICE_SET_NFK = "set_nfk"
SERVICE_SKIP_NEXT = "skip_next_run"
SERVICE_IMPORT_NODE_RED = "import_node_red_state"

# Soil type presets (mm NFK per dm root depth)
SOIL_TYPES = {
    "sand": 8,
    "sandy_loam": 12,
    "loam": 15,
    "clay_loam": 18,
    "clay": 20,
}

# Zone type defaults (Kc per zone type)
# Only lawn types use ET0/NFK-based calculation
# Drip types are time/manually controlled only
ZONE_TYPE_KC = {
    "lawn": 0.8,    # ET0-based, weather-dependent
    "drip": 1.0,    # Time-controlled only, no ET0 calc
}
ZONE_TYPES = list(ZONE_TYPE_KC.keys())

# Scheduling constants
TRAFO_DELAY_S: float = 0.5
FAILSAFE_INTERVAL_MIN: int = 5
DAILY_CALC_HOUR: int = 0
DAILY_CALC_MIN: int = 5
GTS_RESET_MONTH: int = 1
GTS_RESET_DAY: int = 1
DEFAULT_FROST_THRESHOLD_C: float = 4.0
TRAFO_UNAVAILABLE_TIMEOUT_S: int = 120  # 2 minutes
TRAFO_MISMATCH_TIMEOUT_S: int = 30
CATCHUP_MAX_DAYS: int = 3  # more than this → Repair Issue instead of silently catching up

# Sensor clamp limits
SENSOR_LIMITS: dict[str, tuple[float, float]] = {
    "temp": (-50.0, 60.0),
    "humidity": (0.0, 100.0),
    "wind": (0.0, 50.0),
    "solar": (0.0, 1500.0),
    "rain": (0.0, 200.0),
}

# Mode names (used by select entity)
MODE_OFF = "aus"
MODE_SEMI = "semi"
MODE_FULL = "voll"
MODE_SEED = "ansaat"
MODES = [MODE_OFF, MODE_SEMI, MODE_FULL, MODE_SEED]

# ET method names
ET_METHOD_FAO56 = "fao56"
ET_METHOD_HARGREAVES = "hargreaves"
ET_METHOD_HAUDE = "haude"
ET_METHODS = [ET_METHOD_FAO56, ET_METHOD_HARGREAVES, ET_METHOD_HAUDE]

# DWD Forecast API
BRIGHTSKY_API_URL = "https://api.brightsky.dev/weather"
BRIGHTSKY_TIMEOUT_S = 10

# HA platform list (for async_forward_entry_setups)
PLATFORMS = [
    "sensor",
    "binary_sensor",
    "switch",
    "select",
    "number",
    "button",
    "time",
]

# Weekday constants
WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
WEEKDAY_DE = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]
