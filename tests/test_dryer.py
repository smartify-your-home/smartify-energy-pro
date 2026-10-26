"""Regression checks for the dedicated continuous-load dryer."""
import importlib.util
import unittest
from types import SimpleNamespace as NS
from test_load_budget import ROOT, Context, LoadDevice
from unittest.mock import AsyncMock

from test_load_budget import DryerDevice

class DryerChecks(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.values = {"switch.dryer": "on", "sensor.dryer": "0"}
        def get(ent):
            v = self.values.get(ent)
            return NS(state=v, attributes={"unit_of_measurement":"W"}) if v is not None else None
        manager = NS(hass=NS(states=NS(get=get)), hub_mode="auto", async_param_changed=lambda: None,
                     async_request_run=AsyncMock(), device_budgets={})
        self.manager = manager

    def dryer(self, resume):
        dryer = DryerDevice(self.manager, "dryer", "Trockner", {
            "switch": "switch.dryer", "power_sensor": "sensor.dryer",
            "nominal_power": 800, "duration": 2.5, "dryer_resume": resume,
        })
        dryer.params["mode"] = "auto"
        return dryer

    async def test_non_resumable_never_toggles_switch(self):
        dryer = self.dryer("never")
        dryer._switch = AsyncMock()
        ctx = NS(now=__import__("datetime").datetime.now(), dt=30)
        dryer.state["sm"] = "laeuft"
        dryer.state["approved"] = True
        await dryer.async_apply(NS(on=False,setpoint={}), ctx)
        await dryer.async_disabled(ctx)
        self.assertEqual(dryer._switch.await_count, 0)

    def test_nonresumable_hides_start_button_and_deadline(self):
        d = self.dryer("never")
        self.assertEqual([s.key for s in d.button_specs()], ["reset"])
        self.assertNotIn("latest_start", [s.key for s in d.param_specs()])

    def test_resumable_has_start_button_and_deadline(self):
        d = self.dryer("yes")
        self.assertIn("start_now", [s.key for s in d.button_specs()])
        self.assertIn("latest_start", [s.key for s in d.param_specs()])

    def test_continuous_800w_reserved_after_first_heating_phase(self):
        d = self.dryer("yes")
        d.state.update(sm="laeuft",hp_done=True)
        self.values["sensor.dryer"]="120"
        self.assertEqual(d.reserved_power, 800)
        self.values["sensor.dryer"]="950"
        self.assertEqual(d.reserved_power, 950)

if __name__ == "__main__":
    unittest.main()
