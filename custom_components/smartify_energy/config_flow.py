"""Einrichtung: Hub (Netz, Prognose, Speicher) + Geräte als Unterelemente."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector as sel

from .const import (
    BAT_SIGN_CHARGE_POSITIVE,
    BAT_SIGN_DISCHARGE_POSITIVE,
    BOOST_NUMBER,
    BOOST_SWITCH,
    CONF_BAT_CAPACITY,
    CONF_BAT_POWER,
    CONF_BAT_SIGN,
    CONF_BAT_SOC,
    CONF_BOOST_ENTITY,
    CONF_BOOST_TYPE,
    CONF_CAPACITY,
    CONF_CONNECTED_ENTITY,
    CONF_CONNECTED_STATES,
    CONF_CONSUMPTION,
    CONF_CONTROL_ENTITY,
    CONF_CONTROL_OFF,
    CONF_CONTROL_ON,
    CONF_CURRENT_ENTITY,
    CONF_DAYS_ENTITY,
    CONF_DURATION,
    CONF_EFFICIENCY,
    CONF_FORECAST_ENTRIES,
    CONF_FORECAST_SENSORS,
    CONF_GRID_EXPORT_SENSOR,
    CONF_GRID_SENSOR,
    CONF_GRID_SIGN,
    CONF_INTERVAL,
    CONF_MAX_CURRENT,
    CONF_MIN_CURRENT,
    CONF_NAME,
    CONF_NOMINAL,
    CONF_PHASE_1,
    CONF_PHASE_3,
    CONF_PHASE_ENTITY,
    CONF_PHASES,
    CONF_POWER_SENSOR,
    CONF_SINK_SENSORS,
    CONF_SOC_SENSOR,
    CONF_SWITCH,
    CONF_TEMP_SENSOR,
    CONF_VOLTAGE,
    DOMAIN,
    GRID_SIGN_EXPORT_POSITIVE,
    GRID_SIGN_IMPORT_POSITIVE,
    NAME,
    TYPE_EV,
    TYPE_HEATPUMP,
    TYPE_LOAD,
    TYPE_POOL,
)
from .forecast import async_default_forecast_entries, async_forecast_entry_options

SWITCH_DOMAINS = ["switch", "input_boolean", "light"]


# ── Selektoren ───────────────────────────────────────────────────────────────
def _ent(domain: str | list[str], device_class: str | None = None, multiple: bool = False) -> sel.EntitySelector:
    cfg: dict[str, Any] = {"domain": domain, "multiple": multiple}
    if device_class:
        cfg["device_class"] = device_class
    return sel.EntitySelector(sel.EntitySelectorConfig(**cfg))


def _num(low: float, high: float, step: float = 1, unit: str | None = None) -> sel.NumberSelector:
    cfg: dict[str, Any] = {"min": low, "max": high, "step": step, "mode": sel.NumberSelectorMode.BOX}
    if unit:
        cfg["unit_of_measurement"] = unit
    return sel.NumberSelector(sel.NumberSelectorConfig(**cfg))


def _choice(options: list[str], key: str) -> sel.SelectSelector:
    return sel.SelectSelector(sel.SelectSelectorConfig(options=options, translation_key=key))


def _opt(key: str, defaults: dict, default: Any = None) -> vol.Optional:
    """Optionales Feld mit vorgeschlagenem Wert (lässt sich leeren)."""
    val = defaults.get(key, default)
    return vol.Optional(key, description={"suggested_value": val} if val not in (None, "", []) else None)


def _req(key: str, defaults: dict, default: Any = None) -> vol.Required:
    val = defaults.get(key, default)
    return vol.Required(key, default=val) if val is not None else vol.Required(key)


def _clean(data: dict) -> dict:
    return {k: v for k, v in data.items() if v not in (None, "", [])}


# ── Hub-Schritte ─────────────────────────────────────────────────────────────
def _grid_schema(d: dict, with_name: bool) -> vol.Schema:
    fields: dict = {}
    if with_name:
        fields[_req(CONF_NAME, d, NAME)] = sel.TextSelector()
    fields.update({
        _req(CONF_GRID_SENSOR, d): _ent("sensor", "power"),
        _req(CONF_GRID_SIGN, d, GRID_SIGN_EXPORT_POSITIVE): _choice(
            [GRID_SIGN_EXPORT_POSITIVE, GRID_SIGN_IMPORT_POSITIVE], "grid_sign"),
        _opt(CONF_GRID_EXPORT_SENSOR, d): _ent("sensor", "power"),
        _opt(CONF_SINK_SENSORS, d): _ent("sensor", "power", multiple=True),
        _req(CONF_INTERVAL, d, 30): _num(10, 120, 5, "s"),
    })
    return vol.Schema(fields)


def _forecast_schema(d: dict, options: list[dict[str, str]]) -> vol.Schema:
    fields: dict = {}
    if options:
        fields[_opt(CONF_FORECAST_ENTRIES, d)] = sel.SelectSelector(
            sel.SelectSelectorConfig(options=options, multiple=True, mode=sel.SelectSelectorMode.LIST))
    fields[_opt(CONF_FORECAST_SENSORS, d)] = _ent("sensor", multiple=True)
    return vol.Schema(fields)


def _battery_schema(d: dict) -> vol.Schema:
    return vol.Schema({
        _opt(CONF_BAT_SOC, d): _ent("sensor", "battery"),
        _opt(CONF_BAT_POWER, d): _ent("sensor", "power"),
        _req(CONF_BAT_SIGN, d, BAT_SIGN_CHARGE_POSITIVE): _choice(
            [BAT_SIGN_CHARGE_POSITIVE, BAT_SIGN_DISCHARGE_POSITIVE], "battery_sign"),
        _opt(CONF_BAT_CAPACITY, d): _num(0, 200, 0.1, "kWh"),
    })


class _HubSteps:
    """Gemeinsame Schritte für Einrichtung und Optionen."""

    data: dict[str, Any]

    async def _forecast_defaults(self) -> list[str]:
        if CONF_FORECAST_ENTRIES in self.data:
            return self.data[CONF_FORECAST_ENTRIES]
        return await async_default_forecast_entries(self.hass)  # type: ignore[attr-defined]

    async def async_step_forecast(self, user_input: dict | None = None):
        if user_input is not None:
            self.data.pop(CONF_FORECAST_ENTRIES, None)
            self.data.pop(CONF_FORECAST_SENSORS, None)
            self.data.update(_clean(user_input))
            return await self.async_step_battery()
        options = await async_forecast_entry_options(self.hass)  # type: ignore[attr-defined]
        valid = {o["value"] for o in options}
        # Nur existierende Einträge vorschlagen (Energie-Dashboard kann gelöschte IDs enthalten)
        defaults = {**self.data, CONF_FORECAST_ENTRIES: [
            e for e in await self._forecast_defaults() if e in valid]}
        return self.async_show_form(  # type: ignore[attr-defined]
            step_id="forecast", data_schema=_forecast_schema(defaults, options))

    async def async_step_battery(self, user_input: dict | None = None):
        if user_input is not None:
            for key in (CONF_BAT_SOC, CONF_BAT_POWER, CONF_BAT_CAPACITY):
                self.data.pop(key, None)
            self.data.update(_clean(user_input))
            return self._finish()
        return self.async_show_form(step_id="battery", data_schema=_battery_schema(self.data))  # type: ignore[attr-defined]

    def _finish(self):
        raise NotImplementedError


class SmartifyEnergyConfigFlow(_HubSteps, ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self.data.update(_clean(user_input))
            return await self.async_step_forecast()
        return self.async_show_form(step_id="user", data_schema=_grid_schema(self.data, True))

    def _finish(self) -> ConfigFlowResult:
        title = self.data.pop(CONF_NAME, NAME)
        return self.async_create_entry(title=title, data=self.data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SmartifyEnergyOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            TYPE_LOAD: LoadSubentryFlow,
            TYPE_POOL: PoolSubentryFlow,
            TYPE_EV: EvSubentryFlow,
            TYPE_HEATPUMP: HeatPumpSubentryFlow,
        }


class SmartifyEnergyOptionsFlow(_HubSteps, OptionsFlow):
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        if not self.data:
            self.data = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            self.data.pop(CONF_SINK_SENSORS, None)
            self.data.pop(CONF_GRID_EXPORT_SENSOR, None)
            self.data.update(_clean(user_input))
            return await self.async_step_forecast()
        return self.async_show_form(step_id="init", data_schema=_grid_schema(self.data, False))

    def _finish(self) -> ConfigFlowResult:
        return self.async_create_entry(data=self.data)


# ── Geräte (Subentries) ──────────────────────────────────────────────────────
class _DeviceFlow(ConfigSubentryFlow):
    """Gemeinsamer Ablauf: Formular → anlegen bzw. ändern."""

    def schema(self, d: dict) -> vol.Schema:
        raise NotImplementedError

    def validate(self, data: dict) -> dict[str, str]:
        return {}

    async def _form(self, step_id: str, user_input: dict | None, defaults: dict) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(user_input)
            errors = self.validate(data)
            if not errors:
                if step_id == "reconfigure":
                    return self.async_update_and_abort(
                        self._get_entry(), self._get_reconfigure_subentry(),
                        title=data.get(CONF_NAME), data=data)
                return self.async_create_entry(title=data[CONF_NAME], data=data)
            defaults = data
        return self.async_show_form(step_id=step_id, data_schema=self.schema(defaults), errors=errors)

    async def async_step_user(self, user_input: dict | None = None) -> SubentryFlowResult:
        return await self._form("user", user_input, {})

    async def async_step_reconfigure(self, user_input: dict | None = None) -> SubentryFlowResult:
        return await self._form("reconfigure", user_input, dict(self._get_reconfigure_subentry().data))


class LoadSubentryFlow(_DeviceFlow):
    def schema(self, d: dict) -> vol.Schema:
        return vol.Schema({
            _req(CONF_NAME, d): sel.TextSelector(),
            _req(CONF_SWITCH, d): _ent(SWITCH_DOMAINS),
            _opt(CONF_POWER_SENSOR, d): _ent("sensor", "power"),
            _req(CONF_NOMINAL, d, 2200): _num(100, 4000, 50, "W"),
            _req(CONF_DURATION, d, 2.0): _num(0.5, 6, 0.25, "h"),
        })


class PoolSubentryFlow(_DeviceFlow):
    def schema(self, d: dict) -> vol.Schema:
        return vol.Schema({
            _req(CONF_NAME, d, "Poolpumpe"): sel.TextSelector(),
            _req(CONF_SWITCH, d): _ent(SWITCH_DOMAINS),
            _opt(CONF_POWER_SENSOR, d): _ent("sensor", "power"),
            _req(CONF_NOMINAL, d, 700): _num(50, 3000, 10, "W"),
            _opt(CONF_TEMP_SENSOR, d): _ent("sensor", "temperature"),
        })


class EvSubentryFlow(_DeviceFlow):
    def schema(self, d: dict) -> vol.Schema:
        return vol.Schema({
            _req(CONF_NAME, d, "Wallbox"): sel.TextSelector(),
            _req(CONF_CURRENT_ENTITY, d): _ent(["number", "input_number"]),
            _req(CONF_CONTROL_ENTITY, d): _ent(["switch", "input_boolean", "select", "input_select"]),
            _opt(CONF_CONTROL_ON, d, "charge"): sel.TextSelector(),
            _opt(CONF_CONTROL_OFF, d, "dont_charge"): sel.TextSelector(),
            _opt(CONF_PHASE_ENTITY, d): _ent(["select", "input_select"]),
            _opt(CONF_PHASE_1, d, "one_phase"): sel.TextSelector(),
            _opt(CONF_PHASE_3, d, "three_phases"): sel.TextSelector(),
            _opt(CONF_POWER_SENSOR, d): _ent("sensor", "power"),
            _opt(CONF_CONNECTED_ENTITY, d): _ent(["sensor", "binary_sensor"]),
            _opt(CONF_CONNECTED_STATES, d): sel.TextSelector(),
            _opt(CONF_SOC_SENSOR, d): _ent("sensor", "battery"),
            _req(CONF_CAPACITY, d, 60): _num(5, 200, 0.1, "kWh"),
            _req(CONF_CONSUMPTION, d, 18): _num(5, 40, 0.1, "kWh/100km"),
            _opt(CONF_DAYS_ENTITY, d): _ent(["input_text", "sensor"]),
            _req(CONF_MIN_CURRENT, d, 6): _num(6, 32, 1, "A"),
            _req(CONF_MAX_CURRENT, d, 16): _num(6, 32, 1, "A"),
            _req(CONF_PHASES, d, 3): _num(1, 3, 2),
            _req(CONF_VOLTAGE, d, 230): _num(200, 250, 1, "V"),
            _req(CONF_EFFICIENCY, d, 90): _num(50, 100, 1, "%"),
        })

    def validate(self, data: dict) -> dict[str, str]:
        ctrl = data.get(CONF_CONTROL_ENTITY, "")
        if ctrl.split(".")[0] in ("select", "input_select") and not (data.get(CONF_CONTROL_ON) and data.get(CONF_CONTROL_OFF)):
            return {CONF_CONTROL_ON: "options_required"}
        if data.get(CONF_PHASE_ENTITY) and not (data.get(CONF_PHASE_1) and data.get(CONF_PHASE_3)):
            return {CONF_PHASE_1: "options_required"}
        if float(data.get(CONF_MIN_CURRENT, 6)) > float(data.get(CONF_MAX_CURRENT, 16)):
            return {CONF_MAX_CURRENT: "min_gt_max"}
        return {}


class HeatPumpSubentryFlow(_DeviceFlow):
    def schema(self, d: dict) -> vol.Schema:
        return vol.Schema({
            _req(CONF_NAME, d, "Wärmepumpe Boost"): sel.TextSelector(),
            _req(CONF_BOOST_TYPE, d, BOOST_SWITCH): _choice([BOOST_SWITCH, BOOST_NUMBER], "boost_type"),
            _req(CONF_BOOST_ENTITY, d): _ent(["switch", "input_boolean", "number", "input_number"]),
            _opt(CONF_POWER_SENSOR, d): _ent("sensor", "power"),
            _req(CONF_NOMINAL, d, 2000): _num(200, 10000, 50, "W"),
            _opt(CONF_TEMP_SENSOR, d): _ent("sensor", "temperature"),
        })

    def validate(self, data: dict) -> dict[str, str]:
        dom = data.get(CONF_BOOST_ENTITY, "").split(".")[0]
        is_num = dom in ("number", "input_number")
        if is_num != (data.get(CONF_BOOST_TYPE) == BOOST_NUMBER):
            return {CONF_BOOST_ENTITY: "boost_mismatch"}
        return {}
