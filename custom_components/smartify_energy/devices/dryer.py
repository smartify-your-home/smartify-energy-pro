"""Dryer profile: long continuous power, optionally non-interruptible controls."""
from __future__ import annotations

from datetime import timedelta

from .base import BaseDevice, Context, Decision
from .load import DETECTED, FINISHED, IDLE, RUNNING, WAITING, LoadDevice


class DryerDevice(LoadDevice):
    TYPE = "dryer"
    ICON = "mdi:tumble-dryer"

    def param_specs(self):
        specs = super().param_specs()
        if self.cfg.get("dryer_resume", "never") == "yes":
            return specs
        return [s for s in specs if s.key in {
            "nominal_power", "finish_threshold", "finish_minutes", "duration"
        }]

    def button_specs(self):
        specs = super().button_specs()
        return specs if self.can_resume else [s for s in specs if s.key == "reset"]

    def status_attrs(self):
        return {
            **super().status_attrs(),
            "wiederanlauf": self.can_resume,
            "steckdose_von_sep_gesteuert": self.can_resume,
            "dauerlast_reservierung": True,
        }

    @property
    def can_resume(self) -> bool:
        return self.cfg.get("dryer_resume", "never") == "yes"

    @property
    def reserved_power(self) -> float:
        # Unlike episodic washer heating, allocate the expected long-load
        # headroom for the entire approved program.
        actual = self.power_accounted_in_grid()
        if self.state["sm"] == RUNNING:
            return max(self.nominal, actual)
        return actual

    def decide(self, ctx: Context, budget_left: float) -> Decision:
        if self.can_resume:
            return super().decide(ctx, budget_left)
        # Non-resumable dryers must NEVER have their plug switched by SEP.
        # Their physical start is manual; SEP can only monitor and reserve.
        on = self.is_on()
        p = self._p() if on else 0
        sm = self.state["sm"]
        if sm == FINISHED:
            self.status = FINISHED
            return Decision(on, p, "Fertig – Reset erforderlich")
        if sm in (IDLE, DETECTED, WAITING):
            if on and p > 9:
                if self._detected_since is None:
                    self._detected_since = ctx.now
                if ctx.now - self._detected_since >= timedelta(seconds=5):
                    self.state.update(sm=RUNNING, approved=True, forced_start=False,
                                      since=ctx.now.timestamp(), hp_done=False)
                    self._detected_since = None
            else:
                self._detected_since = None
            if self.state["sm"] != RUNNING:
                self.status = IDLE
                return Decision(on, p, "Manuell am Trockner starten; Steckdose bleibt eingeschaltet")
        self.status = RUNNING
        return Decision(True, self.reserved_power,
                        "Nicht unterbrechbarer Trockner läuft – Steckdose bleibt unangetastet")

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        if self.can_resume:
            await super().async_apply(decision, ctx)
        # Else intentionally no switch calls, including after finishing.

    async def async_run(self, ctx: Context, budget_left: float) -> Decision:
        if self.can_resume:
            return await super().async_run(ctx, budget_left)
        # Avoid LoadDevice's hub-off plug manipulation for non-resumable models.
        return await BaseDevice.async_run(self, ctx, budget_left)

    async def async_disabled(self, ctx: Context) -> None:
        if self.can_resume:
            await super().async_disabled(ctx)
        # Never switch off a non-resumable dryer.

    async def async_start_now(self) -> None:
        if self.can_resume:
            await super().async_start_now()
        # Manual-start models cannot be started by restoring socket power.
