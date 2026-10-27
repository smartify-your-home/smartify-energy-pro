"""Basisklasse für gesteuerte Geräte."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..const import DEVICE_MODES, MODE_AUTO, MODE_MANUAL, MODE_OBSERVE, MODE_OFF
from ..helpers import BinarySpec, ButtonSpec, ParamSpec, SensorSpec, power_w
from ..reasons import localize_reason
from ..status import STATUS_CODES

if TYPE_CHECKING:
    from ..manager import EnergyManager

_LOGGER = logging.getLogger(__name__)
ACTOR_FIELDS = {
    "load": ("switch",), "dryer": ("switch",), "pool": ("switch",), "heater": ("switch",),
    "ev": ("control_entity", "current_entity", "phase_entity"), "heatpump": ("boost_entity",),
}
ENTITY_FIELDS = {
    "load": ("switch", "power_sensor"), "dryer": ("switch", "power_sensor"),
    "pool": ("switch", "power_sensor"), "heater": ("switch", "power_sensor", "temperature_sensor"),
    "ev": ("control_entity", "current_entity", "phase_entity", "connected_entity", "soc_sensor",
           "days_entity", "power_sensor"),
    "heatpump": ("boost_entity", "power_sensor", "temperature_sensor", "ww_active_entity",
                 "ww_boost_temp_entity", "sun_angle_entity", "cloud_now_entity", "cloud_next_entity"),
}


@dataclass
class Context:
    """Daten eines Regelzyklus."""

    now: datetime
    dt: float                  # Sekunden seit letztem Zyklus
    budget_now: float          # aktueller Überschuss inkl. Verbrauch gesteuerter Geräte (W)
    budget_avg: float          # Mittelwert über das Mittelungsfenster (W)
    budget_short: float        # Mittelwert über 2 min (W)
    history_ready: bool        # Mittelungsfenster voll
    night_window: bool         # globales Sofortfenster aktiv
    alloc_base: float = 0.0    # Basis der Verteilung (Mittelwert, sonst Momentanwert)
    trend_delta: float = 0.0
    trend_ready: bool = False
    loads_heating: list[str] = field(default_factory=list)  # Verbraucher in Heizphase

    def now_left(self, budget_left: float) -> float:
        """Restbudget bezogen auf den Momentanwert statt den Mittelwert."""
        return budget_left + (self.budget_now - self.alloc_base)

    def short_left(self, budget_left: float) -> float:
        """Restbudget bezogen auf den 2-Minuten-Mittelwert."""
        return budget_left + (self.budget_short - self.alloc_base)


@dataclass
class Decision:
    """Ergebnis der Entscheidung eines Geräts."""

    on: bool
    power: float = 0.0          # reservierte Leistung (W)
    reason: str = ""
    forced: bool = False        # unabhängig vom Überschuss (Pflicht/Deadline)
    setpoint: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanDemand:
    """Bedarf für den Prognose-Planer."""

    power: float               # W während des Betriebs
    energy: float              # benötigte Energie (Wh)
    deadline: datetime | None  # spätestens fertig bis
    earliest: datetime | None = None
    interruptible: bool = True


class BaseDevice:
    """Gemeinsame Logik: Modus, Priorität, Parameter, Status."""

    TYPE = "base"
    ICON = "mdi:flash"

    def __init__(self, manager: EnergyManager, subentry_id: str, title: str, cfg: dict) -> None:
        self.manager = manager
        self.hass: HomeAssistant = manager.hass
        self.id = subentry_id
        self.name = title
        self.cfg = cfg
        self.params: dict[str, Any] = {s.key: s.default for s in self.all_param_specs()}
        # Priority is an internal persistent setting, controlled by the dashboard.
        # It is deliberately not exposed as a number entity.
        self.params["priority"] = 5
        self.state: dict[str, Any] = {}
        self.status = "init"
        self._actuator_retry_at = 0.0
        self.reason = ""
        self.would = ""            # Empfehlung im Beobachten-Modus
        self.last_decision: Decision | None = None
        self.plan: dict[str, Any] = {}

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        self._status = STATUS_CODES.get(value, value)

    def observed_entities(self) -> set[str]:
        return {self.cfg[field] for field in ENTITY_FIELDS.get(self.TYPE, ())
                if isinstance(self.cfg.get(field), str) and self.cfg[field]}

    def _actor_unavailable(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        # A never-pressed HA button legitimately has the state 'unknown'.
        return state is None or state.state == "unavailable" or (
            state.state in ("unknown", "") and entity_id.split(".")[0] not in ("button", "input_button"))

    def _unavailable_actor(self) -> str | None:
        return next((self.cfg[key] for key in ACTOR_FIELDS.get(self.TYPE, ())
                     if self.cfg.get(key) and self._actor_unavailable(self.cfg[key])), None)

    async def _call_actor(self, domain: str, service: str, data: dict, **kwargs) -> None:
        entity_id = data["entity_id"]
        if self._actor_unavailable(entity_id):
            raise RuntimeError("Actuator unavailable")
        async with asyncio.timeout(10):
            await self.hass.services.async_call(domain, service, data, **kwargs)

    # ── Parameter ────────────────────────────────────────────────────────────
    def base_param_specs(self) -> list[ParamSpec]:
        return [
            ParamSpec("mode", "select", MODE_OBSERVE, "mdi:cog-transfer", options=DEVICE_MODES, config=False),
        ]

    def param_specs(self) -> list[ParamSpec]:
        return []

    def all_param_specs(self) -> list[ParamSpec]:
        return self.base_param_specs() + self.param_specs()

    def p(self, key: str) -> Any:
        return self.params.get(key)

    def set_param(self, key: str, value: Any) -> None:
        self.params[key] = value
        self.on_param_changed(key)
        self.manager.async_param_changed()

    def on_param_changed(self, key: str) -> None:
        """Hook für Unterklassen."""

    # ── Entity-Beschreibungen ────────────────────────────────────────────────
    def sensor_specs(self) -> list[SensorSpec]:
        return [
            SensorSpec("status", lambda: self.status, self.status_attrs, icon=self.ICON),
            SensorSpec(
                "planned_start",
                lambda: self.plan.get("start"),
                lambda: {k: v for k, v in self.plan.items() if k != "start"},
                device_class="timestamp",
                icon="mdi:calendar-clock",
            ),
            SensorSpec("power", lambda: round(self.power_now(), 0), unit="W",
                       device_class="power", state_class="measurement"),
        ]

    def binary_specs(self) -> list[BinarySpec]:
        return [BinarySpec("active", lambda: self.is_on(), icon="mdi:power", device_class="running")]

    def button_specs(self) -> list[ButtonSpec]:
        return []

    def status_attrs(self) -> dict:
        d = self.last_decision
        return {
            "geraetetyp": self.TYPE,
            "modus": self.mode,
            "prioritaet": self.priority,
            "grund": self.reason,
            "reason": localize_reason(self.reason, getattr(getattr(self.hass, "config", None), "language", "de")),
            "status_code": self.status,
            "legacy_status": next((key for key, value in STATUS_CODES.items() if value == self.status), self.status),
            "empfehlung": self.would,
            "reserviert_w": round(d.power) if d and d.on else 0,
            "pflicht": bool(d and d.forced),
            # Snapshot of the budget available at this device's priority
            # position (before its own start). Used by SEP's priority card.
            **self.manager.device_budgets.get(self.id, {}),
        }

    # ── Zustand ──────────────────────────────────────────────────────────────
    @property
    def mode(self) -> str:
        hub_mode = self.manager.hub_mode
        if hub_mode == MODE_OFF:
            return MODE_OFF
        if hub_mode == MODE_OBSERVE and self.p("mode") == MODE_AUTO:
            return MODE_OBSERVE
        return self.p("mode")

    @property
    def priority(self) -> int:
        return int(self.p("priority") or 5)

    @property
    def participates(self) -> bool:
        """Verbrauch zählt zum steuerbaren Budget (Auto oder Beobachten)."""
        return self.mode in (MODE_AUTO, MODE_OBSERVE)

    def is_on(self) -> bool:
        raise NotImplementedError

    def power_now(self) -> float:
        sensor = self.cfg.get("power_sensor")
        if sensor:
            val = power_w(self.hass, sensor)
            if val is not None:
                return max(val, 0.0)
        return float(self.nominal) if self.is_on() else 0.0

    def power_accounted_in_grid(self) -> float:
        """Measured consumption already embedded in the physical grid balance."""
        return self.power_now()

    def reclaimable_power(self) -> float:
        """Only power SEP can reliably curtail may increase another device's budget."""
        return 0.0

    def own_budget_power(self, measured_w: float, reclaimed_w: float) -> float:
        """Own existing load may be considered for maintaining/modulating itself."""
        return 0.0

    @property
    def nominal(self) -> float:
        return float(self.p("nominal_power") or self.cfg.get("nominal_power") or 1000)

    def sort_key(self, ctx: Context) -> tuple:
        return (self.priority, self.state.get("since") or ctx.now.timestamp())

    # ── Ablauf je Zyklus ─────────────────────────────────────────────────────
    def pre_update(self, ctx: Context) -> None:
        """Messwerte/Laufzeiten fortschreiben (jeder Modus)."""

    def decide(self, ctx: Context, budget_left: float) -> Decision:
        raise NotImplementedError

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        raise NotImplementedError

    async def async_run(self, ctx: Context, budget_left: float) -> Decision:
        mode = self.mode
        unavailable = self._unavailable_actor()
        if unavailable:
            self.status, self.reason, self.would = "actuator_unavailable", "Aktor nicht verfügbar", ""
            self.last_decision = Decision(False, reason=self.reason)
            return self.last_decision
        if ctx.now.timestamp() < self._actuator_retry_at:
            self.status = "actuator_error"
            return self.last_decision or Decision(False, reason="Aktor-Wiederholpause")
        if mode == MODE_OFF:
            self.status, self.reason, self.would = "aus", "Modus: Aus", ""
            self.last_decision = Decision(False, reason="Modus: Aus")
            try:
                await self.async_disabled(ctx)
            except Exception:
                self.status = "actuator_error"
                self._actuator_retry_at = ctx.now.timestamp() + 30
                raise
            return self.last_decision
        if mode == MODE_MANUAL:
            self.status, self.reason, self.would = "manuell", "Modus: Manuell – keine Steuerung", ""
            self.last_decision = Decision(False, reason=self.reason)
            return self.last_decision
        decision = self.decide(ctx, budget_left)
        self.last_decision = decision
        self.reason = decision.reason
        if mode == MODE_AUTO:
            self.would = ""
            try:
                await self.async_apply(decision, ctx)
            except Exception:
                self.status = "actuator_error"
                self._actuator_retry_at = ctx.now.timestamp() + 30
                raise
        else:
            self.would = ("EIN" if decision.on else "AUS") + (f" – {decision.reason}" if decision.reason else "")
            self.status = "beobachten"
        return decision

    async def async_disabled(self, ctx: Context) -> None:
        """Wird im Modus Aus aufgerufen."""

    def plan_demand(self, now: datetime) -> PlanDemand | None:
        return None

    # ── Persistenz ───────────────────────────────────────────────────────────
    def dump(self) -> dict:
        return {"params": self.params, "state": self._dump_state(), "cfg": self.cfg}

    def load(self, data: dict) -> None:
        old_cfg = data.get("cfg") or {}
        for k, v in (data.get("params") or {}).items():
            if k not in self.params:
                continue
            if k in self.cfg and old_cfg.get(k) != self.cfg.get(k):
                continue  # in der Gerätekonfiguration geändert → neuer Wert gilt
            self.params[k] = v
        self._load_state(data.get("state") or {})

    def _dump_state(self) -> dict:
        return {k: v for k, v in self.state.items() if isinstance(v, (int, float, str, bool, type(None)))}

    def _load_state(self, state: dict) -> None:
        self.state.update(state)

    # ── Aktoren ──────────────────────────────────────────────────────────────
    async def _switch(self, entity_id: str, on: bool) -> None:
        domain = entity_id.split(".")[0]
        if domain not in ("switch", "input_boolean", "light", "fan"):
            domain = "homeassistant"
        await self._call_actor(
            domain, "turn_on" if on else "turn_off", {"entity_id": entity_id}, blocking=True
        )
        _LOGGER.info("[%s] %s → %s (%s)", self.name, entity_id, "EIN" if on else "AUS", self.reason)
