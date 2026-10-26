"""Konstanten für den Smartify Energy Pro."""
from __future__ import annotations

DOMAIN = "smartify_energy"
NAME = "Smartify Energy Pro"
MANUFACTURER = "smartify"
VERSION = "0.2.22"

PLATFORMS = ["sensor", "binary_sensor", "select", "number", "switch", "time", "button"]

# ── Hub-Konfiguration ────────────────────────────────────────────────────────
CONF_GRID_SENSOR = "grid_sensor"
CONF_GRID_SIGN = "grid_sign"
CONF_GRID_EXPORT_SENSOR = "grid_export_sensor"  # optional: getrennter Einspeise-Sensor
GRID_SIGN_EXPORT_POSITIVE = "export_positive"
GRID_SIGN_IMPORT_POSITIVE = "import_positive"
CONF_SINK_SENSORS = "sink_sensors"          # externe Überschusssenken, informativ (ohne Stellzugriff nicht rückrechenbar)
CONF_FORECAST_ENTRIES = "forecast_entries"  # Config-Entries mit Energie-Plattform (Forecast.Solar, Solcast, …)
CONF_FORECAST_SENSORS = "forecast_sensors"  # Fallback: Sensoren mit Prognose-Attributen
CONF_BAT_SOC = "battery_soc"
CONF_BAT_POWER = "battery_power"
CONF_BAT_SIGN = "battery_sign"
BAT_SIGN_CHARGE_POSITIVE = "charge_positive"
BAT_SIGN_DISCHARGE_POSITIVE = "discharge_positive"
CONF_BAT_CAPACITY = "battery_capacity"
CONF_INTERVAL = "interval"

# ── Gerätetypen (Subentries) ─────────────────────────────────────────────────
TYPE_LOAD = "load"
TYPE_POOL = "pool"
TYPE_EV = "ev"
TYPE_HEATPUMP = "heatpump"
TYPE_HEATER = "heater"

# Geräte-Konfiguration
CONF_NAME = "name"
CONF_SWITCH = "switch"
CONF_POWER_SENSOR = "power_sensor"
CONF_NOMINAL = "nominal_power"
CONF_DURATION = "duration"
CONF_TEMP_SENSOR = "temperature_sensor"
CONF_CURRENT_ENTITY = "current_entity"
CONF_CONTROL_ENTITY = "control_entity"
CONF_CONTROL_ON = "control_on"
CONF_CONTROL_OFF = "control_off"
CONF_PHASE_ENTITY = "phase_entity"
CONF_PHASE_1 = "phase_1"
CONF_PHASE_3 = "phase_3"
CONF_CONNECTED_ENTITY = "connected_entity"
CONF_CONNECTED_STATES = "connected_states"
CONF_SOC_SENSOR = "soc_sensor"
CONF_CAPACITY = "capacity"
CONF_CONSUMPTION = "consumption"
CONF_MIN_CURRENT = "min_current"
CONF_MAX_CURRENT = "max_current"
CONF_PHASES = "phases"
CONF_VOLTAGE = "voltage"
CONF_EFFICIENCY = "efficiency"
CONF_DAYS_ENTITY = "days_entity"
CONF_BOOST_ENTITY = "boost_entity"
CONF_BOOST_TYPE = "boost_type"
CONF_WW_ACTIVE_ENTITY = "ww_active_entity"
BOOST_SWITCH = "switch"
BOOST_BUTTON = "button"
BOOST_NUMBER = "number"

# ── Modi ─────────────────────────────────────────────────────────────────────
MODE_AUTO = "auto"
MODE_OBSERVE = "observe"
MODE_MANUAL = "manual"
MODE_OFF = "off"
DEVICE_MODES = [MODE_AUTO, MODE_OBSERVE, MODE_MANUAL, MODE_OFF]
HUB_MODES = [MODE_AUTO, MODE_OBSERVE, MODE_OFF]

BAT_STRATEGY_FORECAST = "forecast"
BAT_STRATEGY_BATTERY = "battery_first"
BAT_STRATEGY_DEVICES = "devices_first"
BAT_STRATEGIES = [BAT_STRATEGY_FORECAST, BAT_STRATEGY_BATTERY, BAT_STRATEGY_DEVICES]

EV_GOAL_PV = "pv_only"
EV_GOAL_KM = "km_until"
EV_GOAL_DAYS = "days"
EV_GOAL_NOW = "now"
EV_GOALS = [EV_GOAL_PV, EV_GOAL_KM, EV_GOAL_DAYS, EV_GOAL_NOW]

EV_PHASE_AUTO = "auto"
EV_PHASE_1 = "one"
EV_PHASE_3 = "three"
EV_PHASE_MODES = [EV_PHASE_AUTO, EV_PHASE_1, EV_PHASE_3]

POOL_SEASON_AUTO = "auto"
POOL_SEASON_SUMMER = "summer"
POOL_SEASON_WINTER = "winter"
POOL_SEASONS = [POOL_SEASON_AUTO, POOL_SEASON_SUMMER, POOL_SEASON_WINTER]

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"
STORAGE_VERSION = 1
