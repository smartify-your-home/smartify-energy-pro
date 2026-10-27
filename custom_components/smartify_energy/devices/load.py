"""Haushaltsgerät über schaltbare Steckdose (Waschmaschine, Trockner, Geschirrspüler).

Übernommene Logik aus Smart Energy Manager v3:
  bereit → Gerät wird am Gerät gestartet (Steckdose an, Leistung > 5 W) → erkannt
  erkannt + Leistung > 100 W → Freigabe prüfen (Sofortfenster, PV-Budget, Mittelwert)
     ok    → läuft (bis fertig, wird nicht mehr unterbrochen)
     nein  → Steckdose AUS → wartet
  wartet → aktuelle UND gemittelte freie Leistung für erwartete Heizlast ausreichend
            / Spätstart / Sofortfenster → Steckdose EIN → läuft
  läuft  → Leistung < Fertig-Schwelle für Fertig-Dauer → fertig (Reset per Taste)
Neu: Reihenfolge über den Prioritätenmanager statt „wer zuerst eingeschaltet wurde“.
Mehrere Heizphasen dürfen gleichzeitig laufen, wenn das gesamte PV-Budget reicht.
Nicht gemessene Last wird konservativ mit der vollen Nennleistung reserviert.
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from homeassistant.util import dt as dt_util

from ..budget import pv_start_remaining
from ..const import CONF_POWER_SENSOR, CONF_SWITCH
from ..helpers import BinarySpec, ButtonSpec, ParamSpec, SensorSpec, is_on, power_w, time_from_str
from .base import BaseDevice, Context, Decision, PlanDemand

_LOGGER = logging.getLogger(__name__)

IDLE, DETECTED, WAITING, RUNNING, FINISHED = "bereit", "erkannt", "wartet", "laeuft", "fertig"


class LoadDevice(BaseDevice):
    TYPE = "load"
    ICON = "mdi:washing-machine"

    @property
    def appliance_icon(self) -> str:
        return {"washing_machine": "mdi:washing-machine",
                "dishwasher": "mdi:dishwasher",
                "other": "mdi:power-plug"}.get(self.cfg.get("appliance_type", "washing_machine"), self.ICON)

    def status_attrs(self) -> dict:
        return {**super().status_attrs(), "icon": self.appliance_icon,
                "haushaltsgeraet_typ": self.cfg.get("appliance_type", "washing_machine")}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state.setdefault("sm", IDLE)
        self.state.setdefault("approved", False)
        self.state.setdefault("hp_active", False)
        self.state.setdefault("hp_done", False)
        self._detected_since: datetime | None = None
        self._hp_since: datetime | None = None
        self._low_since: datetime | None = None
        self._finished_off_seen = False
        self._nachladen_prev = False
        self._hub_released = False

    def param_specs(self) -> list[ParamSpec]:
        return [
            ParamSpec("nominal_power", "number", float(self.cfg.get("nominal_power", 2200)),
                      "mdi:flash", 100, 4000, 50, "W"),
            ParamSpec("min_surplus", "number", 1500, "mdi:solar-power", -3000, 4000, 50, "W"),
            ParamSpec("earliest_start", "time", "00:00", "mdi:clock-start"),
            ParamSpec("latest_start", "time", "16:00", "mdi:clock-alert-outline"),
            ParamSpec("finish_threshold", "number", 5, "mdi:power-plug-off", 0, 50, 0.5, "W"),
            ParamSpec("finish_minutes", "number", 2, "mdi:timer-sand", 1, 60, 1, "min"),
            ParamSpec("duration", "number", float(self.cfg.get("duration", 2.0)),
                      "mdi:timer-outline", 0.5, 6, 0.25, "h"),
            ParamSpec("nachladen", "switch", False, "mdi:washing-machine-alert", config=False),
        ]

    def sensor_specs(self) -> list[SensorSpec]:
        specs = super().sensor_specs()
        for spec in specs:
            if spec.key == "status":
                spec.icon = self.appliance_icon
        return specs + [
            SensorSpec("phase", lambda: self.state.get("sm"), icon="mdi:state-machine", diagnostic=True),
        ]

    def binary_specs(self) -> list[BinarySpec]:
        return super().binary_specs() + [
            BinarySpec("waiting", lambda: self.state.get("sm") == WAITING, "mdi:timer-pause-outline"),
            BinarySpec("heating", lambda: bool(self.state.get("hp_active")), "mdi:heat-wave"),
            BinarySpec("finished", lambda: self.state.get("sm") == FINISHED, "mdi:check-circle-outline"),
        ]

    def button_specs(self) -> list[ButtonSpec]:
        return [
            ButtonSpec("start_now", self.async_start_now, "mdi:play-circle"),
            ButtonSpec("reset", self.async_reset, "mdi:restart"),
        ]

    # ── Zustand ──────────────────────────────────────────────────────────────
    @property
    def switch(self) -> str:
        return self.cfg[CONF_SWITCH]

    def is_on(self) -> bool:
        return is_on(self.hass, self.switch)

    def _p(self) -> float:
        sensor = self.cfg.get(CONF_POWER_SENSOR)
        if not sensor:
            return self.nominal if self.is_on() else 0.0
        return self.power_now()

    def sort_key(self, ctx: Context) -> tuple:
        return (self.priority, self.state.get("since") or ctx.now.timestamp())

    def power_accounted_in_grid(self) -> float:
        """Credit only actual meter readings, never the nominal fallback.

        If no meter is present or it is unavailable, the full heating
        requirement is reserved; otherwise an assumed nominal wattage could
        cancel its own reservation without real measurement.
        """
        measured = power_w(self.hass, self.cfg.get(CONF_POWER_SENSOR))
        return max(0.0, measured) if measured is not None else 0.0

    @property
    def pv_start_need(self) -> float:
        """Safe PV start must cover heating draw and configured threshold."""
        return max(self.nominal, float(self.p("min_surplus")))

    def _pv_start_headroom(self, ctx: Context, budget_left: float,
                           sw_on: bool) -> tuple[float, float, float]:
        """Explicitly check NOW and the ten-minute average independently.

        Earlier devices may reserve unmet heater power. Their reservations
        are deducted from BOTH budgets before this device can receive a PV
        approval. Metered power is already accounted for at the grid meter.
        """
        own_measured = self.power_accounted_in_grid() if sw_on else 0.0
        return pv_start_remaining(
            ctx.budget_now, ctx.budget_avg, ctx.alloc_base,
            budget_left, own_metered_w=own_measured,
        )

    def _trend_allows_start(self, ctx: Context) -> bool:
        """Only automatic PV starts need a stable or rising trend."""
        return ctx.trend_ready and ctx.trend_delta >= -float(getattr(self.manager, "p", lambda _key: 100)("trend_tolerance"))

    def _trend_wait_reason(self, ctx: Context) -> str:
        if not ctx.trend_ready:
            return "PV-Trend: Messhistorie noch nicht vollständig"
        return (f"PV-Trend fällt um {-ctx.trend_delta:.0f} W "
                f"(Toleranz {float(getattr(self.manager, 'p', lambda _key: 100)('trend_tolerance')):.0f} W)")

    def _reset(self) -> None:
        self.state.update(sm=IDLE, approved=False, forced_start=False, hp_active=False, hp_done=False, since=None)
        self._detected_since = None
        self._hp_since = None
        self._low_since = None
        self._finished_off_seen = False

    async def async_reset(self) -> None:
        self._reset()
        self.reason = "Reset"
        await self.manager.async_request_run()

    async def async_start_now(self) -> None:
        self.state.update(sm=RUNNING, approved=True, forced_start=True, since=dt_util.now().timestamp())
        self.reason = "Sofort-Start"
        if not self.is_on():
            await self._switch(self.switch, True)
        await self.manager.async_request_run()

    # ── Laufende Messung ─────────────────────────────────────────────────────
    def pre_update(self, ctx: Context) -> None:
        sm = self.state["sm"]
        p = self._p()
        if sm in (DETECTED, RUNNING):
            self._check_heating(p, ctx.now)
        if sm == RUNNING:
            done_possible = self.state["hp_done"] or not self.cfg.get(CONF_POWER_SENSOR) or self.state["approved"]
            if done_possible and p < float(self.p("finish_threshold")):
                if self._low_since is None:
                    self._low_since = ctx.now
                elif ctx.now - self._low_since >= timedelta(minutes=float(self.p("finish_minutes"))):
                    _LOGGER.info("[%s] fertig", self.name)
                    self._reset()
                    self.state["sm"] = FINISHED
                    self.reason = "Fertig"
            else:
                self._low_since = None

    def _check_heating(self, p: float, now: datetime) -> None:
        threshold = max(200.0, self.nominal * 0.08)
        if p > threshold:
            if self._hp_since is None:
                self._hp_since = now
            elif now - self._hp_since >= timedelta(seconds=10):
                self.state["hp_active"] = True
                self.state["hp_done"] = False
        else:
            self._hp_since = None
            if self.state["hp_active"] and p < 100:
                self.state["hp_active"] = False
                self.state["hp_done"] = True

    def _new_program_detected(self, ctx: Context, sw_on: bool, p: float) -> bool:
        """Neuer Programmstart im Zustand „fertig“ (ersetzt den Reset-Klick).

        Mit Leistungssensor: wie in „bereit“ 5 s stabil über 9 W.
        Ohne Sensor: Steckdose muss seit „fertig“ einmal aus gewesen sein und
        wieder eingeschaltet werden, sonst würde die noch eingeschaltete
        Steckdose sofort einen neuen Lauf auslösen.
        """
        if not self.cfg.get(CONF_POWER_SENSOR):
            if not sw_on:
                self._finished_off_seen = True
                return False
            return self._finished_off_seen
        if not (sw_on and p > 9):
            self._detected_since = None
            return False
        if self._detected_since is None:
            self._detected_since = ctx.now
            return False
        return ctx.now - self._detected_since >= timedelta(seconds=5)

    @property
    def reserved_power(self) -> float:
        """Laufendes Gerät: Nennleistung bis zum Ende der Heizphase reservieren."""
        p = self._p()
        if self.state["sm"] == RUNNING and not self.state["hp_done"]:
            return max(p, self.nominal)
        return p

    # ── Entscheidung ─────────────────────────────────────────────────────────
    def decide(self, ctx: Context, budget_left: float) -> Decision:
        sm = self.state["sm"]
        p = self._p()
        sw_on = self.is_on()
        latest = time_from_str(self.p("latest_start"), time(16, 0))
        late = ctx.now.time() >= latest
        earliest = time_from_str(self.p("earliest_start"), time(0, 0))
        before_earliest = ctx.now.time() < earliest
        # Positive PV budgets are physical free power plus only genuinely
        # controllable reductions (computed centrally by the manager).
        # A PV start must cover the prospective heating power itself.
        need = self.pv_start_need

        if sm == IDLE:
            # SEM v3: 5 seconds stable above 9 W (or switch on without sensor).
            detected = sw_on and (p > 9 or not self.cfg.get(CONF_POWER_SENSOR))
            if not detected:
                self._detected_since = None
                self.status = "bereit"
                return Decision(False, 0, "Bereit – Gerät am Gerät starten")
            if self._detected_since is None:
                self._detected_since = ctx.now
                self.status = "bereit"
                return Decision(False, 0, "Programmerkennung: 5 Sekunden prüfen")
            if ctx.now - self._detected_since < timedelta(seconds=5):
                self.status = "bereit"
                return Decision(False, 0, "Programmerkennung: 5 Sekunden prüfen")
            self._detected_since = None
            self.state.update(sm=DETECTED, since=ctx.now.timestamp(), approved=False)
            # First detected cycle proceeds to DETECTED below; earliest time is checked there.

        if sm == FINISHED:
            # Finished stays visible until the next program start. A new
            # start (stable draw above 9 W for 5 s) resets automatically and
            # continues with normal detection; the reset button is optional.
            self.status = "fertig"
            if self._new_program_detected(ctx, sw_on, p):
                _LOGGER.info("[%s] neues Programm erkannt – automatischer Reset", self.name)
                self._reset()
                self.state.update(sm=DETECTED, since=ctx.now.timestamp(), approved=False)
                self.reason = "Automatischer Reset – neues Programm erkannt"
                return self.decide(ctx, budget_left)
            return Decision(sw_on, p, "Fertig – neues Programm wird automatisch erkannt")

        if self.state["sm"] == RUNNING and (self.state["approved"]):
            self.status = "laeuft"
            # Do not repeat a historical surplus check when conditions change.
            # A released program must continue even if PV surplus disappears.
            return Decision(True, self.reserved_power,
                            "Programm läuft – bereits freigegeben (kein erneuter PV-Check)",
                            forced=bool(self.state.get("forced_start", False)))

        if self.state["sm"] == DETECTED:
            self.status = "erkannt"
            if p <= 100 and self.cfg.get(CONF_POWER_SENSOR):
                return Decision(True, p, "Programm gewählt – warte auf Start")
            if before_earliest:
                return self._wait(f"Frühester Start erst ab {earliest.strftime('%H:%M')}")
            if ctx.night_window:
                return self._approve("Sofortfenster – freigegeben", forced=True)
            # A newly detected appliance is already drawing some power:
            # that *measured* power has reduced the physical grid export.
            # Add it back only for its own start check, not as credit to
            # any other appliance. Its future reservation remains in the
            # manager (nominal - actually metered draw).
            free_now, free_avg, reserved = self._pv_start_headroom(
                ctx, budget_left, sw_on,
            )
            if not ctx.history_ready:
                return self._wait("Mittelwert noch nicht verfügbar")
            if free_now >= need and free_avg >= need and self._trend_allows_start(ctx):
                return self._approve(
                    f"PV-Freigabe: aktuell {free_now:.0f} W, "
                    f"Ø {free_avg:.0f} W ≥ {need:.0f} W "
                    f"(andere Vorreservierungen {reserved:.0f} W)"
                )
            if free_now >= need and free_avg >= need:
                return self._wait(self._trend_wait_reason(ctx))
            return self._wait(
                f"PV-Budget zu gering: aktuell {free_now:.0f} W, "
                f"Ø {free_avg:.0f} W, benötigt {need:.0f} W "
                f"(andere Vorreservierungen {reserved:.0f} W)"
            )

        if self.state["sm"] == WAITING:
            self.status = "wartet"
            if self.p("nachladen"):
                return Decision(True, p, "Nachladen – Steckdose kurz an", setpoint={"nachladen": True})
            if before_earliest:
                return Decision(False, 0, f"Frühester Start erst ab {earliest.strftime('%H:%M')}")
            if late or ctx.night_window:
                return self._approve("Spätstart/Sofortfenster erreicht", forced=True)
            # No hard lock if another device is heating. The running
            # devices already reserve their still-expected heater draw in
            # the manager. The next appliance can therefore start in
            # parallel if *both* free budgets cover its full heater load.
            if not ctx.history_ready:
                return Decision(False, 0, "Mittelwert noch nicht verfügbar")
            free_now, free_avg, reserved = self._pv_start_headroom(
                ctx, budget_left, sw_on,
            )
            if free_now >= need and free_avg >= need and self._trend_allows_start(ctx):
                return self._approve(
                    f"PV-Freigabe: aktuell {free_now:.0f} W, "
                    f"Ø {free_avg:.0f} W ≥ {need:.0f} W "
                    f"(andere Vorreservierungen {reserved:.0f} W)"
                )
            if free_now >= need and free_avg >= need:
                return Decision(False, 0, self._trend_wait_reason(ctx))
            return Decision(
                False, 0,
                f"Warte auf PV-Budget: aktuell {free_now:.0f} W, "
                f"Ø {free_avg:.0f} W, benötigt {need:.0f} W "
                f"(andere Vorreservierungen {reserved:.0f} W)",
            )

        return Decision(sw_on, p, "Unbekannter Zustand")

    def _approve(self, reason: str, forced: bool = False) -> Decision:
        self.state.update(sm=RUNNING, approved=True, forced_start=forced)
        self.status = "laeuft"
        return Decision(True, max(self._p(), self.nominal), reason, forced=forced)

    def _wait(self, reason: str) -> Decision:
        self.state.update(sm=WAITING, approved=False, hp_active=False, hp_done=False)
        self._detected_since = None
        self._hp_since = None
        self._low_since = None
        self.status = "wartet"
        return Decision(False, 0, reason)

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        sw_on = self.is_on()
        if decision.setpoint.get("nachladen"):
            self._nachladen_prev = True
            if not sw_on:
                await self._switch(self.switch, True)
            return
        if self._nachladen_prev and not self.p("nachladen"):
            self._nachladen_prev = False
        if self.state["sm"] in (IDLE, FINISHED, DETECTED):
            return  # Steckdose bleibt wie vom Benutzer gesetzt
        if decision.on != sw_on:
            await self._switch(self.switch, decision.on)

    async def async_run(self, ctx: Context, budget_left: float) -> Decision:
        if self.manager.hub_mode == "off":
            if not self._hub_released:
                self._reset()
                self.params["nachladen"] = False
                self._nachladen_prev = False
                if not self.is_on():
                    await self._switch(self.switch, True)
                self._hub_released = True
                self.manager.async_param_changed()
            self.status, self.reason, self.would = "manuell", "SEP aus – Steckdose zur manuellen Bedienung freigegeben", ""
            self.last_decision = Decision(False, reason=self.reason)
            return self.last_decision
        self._hub_released = False
        if self.mode == "observe":
            # Beobachten: nur Empfehlung, Zustandsmaschine nicht verändern
            saved = dict(self.state)
            decision = await super().async_run(ctx, budget_left)
            self.state = saved
            return decision
        return await super().async_run(ctx, budget_left)

    # ── Prognose ─────────────────────────────────────────────────────────────
    def plan_demand(self, now: datetime) -> PlanDemand | None:
        if self.state["sm"] not in (DETECTED, WAITING):
            return None
        hours = float(self.p("duration"))
        latest = time_from_str(self.p("latest_start"), time(16, 0))
        latest_dt = now.replace(hour=latest.hour, minute=latest.minute, second=0, microsecond=0)
        if latest_dt < now:
            latest_dt = now
        earliest = time_from_str(self.p("earliest_start"), time(0, 0))
        earliest_dt = now.replace(hour=earliest.hour, minute=earliest.minute, second=0, microsecond=0)
        if earliest_dt < now:
            earliest_dt = now
        return PlanDemand(self.nominal * 0.6, self.nominal * 0.6 * hours,
                          latest_dt + timedelta(hours=hours), earliest=earliest_dt, interruptible=False)
