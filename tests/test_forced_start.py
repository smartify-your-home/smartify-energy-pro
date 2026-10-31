"""A due household deadline must never generate an OFF/ON pulse."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
import unittest

from test_load_budget import Context, DryerDevice, LoadDevice


class ForcedStartTests(unittest.IsolatedAsyncioTestCase):
    def device(self, kind="washing_machine", resume="yes"):
        self.values = {"switch.load": "on", "sensor.load": "500"}
        self.calls = []

        def get(entity):
            value = self.values.get(entity)
            return NS(state=value, attributes={"unit_of_measurement": "W"}) if value is not None else None

        async def call(domain, service, data, **kwargs):
            self.calls.append(service)
            self.values[data["entity_id"]] = "on" if service == "turn_on" else "off"

        manager = NS(hass=NS(states=NS(get=get), services=NS(async_call=call)),
                     hub_mode="auto", async_param_changed=lambda: None)
        cls = DryerDevice if kind == "dryer" else LoadDevice
        d = cls(manager, "load", "Load", {"switch": "switch.load", "power_sensor": "sensor.load",
                "appliance_type": kind, "dryer_resume": resume})
        d.params.update(mode="auto", earliest_start="00:00", latest_start="16:00")
        d.state.update(sm="erkannt", approved=False)
        return d

    def context(self, hour=16, minute=0, night=False):
        return Context(datetime(2026, 10, 31, hour, minute, tzinfo=timezone.utc),
                       2, -1200, -1200, -1200, False, night, alloc_base=-1200)

    async def test_detected_due_deadline_never_switches_off(self):
        for kind in ("washing_machine", "dishwasher", "other", "dryer"):
            with self.subTest(kind=kind):
                d = self.device(kind)
                for _ in range(2):
                    decision = await d.async_run(self.context(), -1200)
                    self.assertTrue(decision.on)
                    self.assertTrue(decision.forced)
                self.assertEqual(self.calls, [])
                self.assertEqual(d.state["sm"], "laeuft")

    async def test_new_program_detection_after_deadline_keeps_socket_on(self):
        d = self.device()
        d.state["sm"] = "bereit"
        ctx = self.context()
        await d.async_run(ctx, -1200)
        ctx.now += timedelta(seconds=5)
        decision = await d.async_run(ctx, -1200)
        self.assertTrue(decision.forced)
        self.assertEqual(self.calls, [])

    async def test_waiting_due_program_only_switches_on(self):
        d = self.device()
        d.state["sm"] = "wartet"
        self.values["switch.load"] = "off"
        decision = await d.async_run(self.context(), -1200)
        self.assertTrue(decision.forced)
        self.assertEqual(self.calls, ["turn_on"])

    async def test_before_deadline_still_waits_for_pv(self):
        d = self.device()
        decision = await d.async_run(self.context(15, 59), -1200)
        self.assertFalse(decision.on)
        self.assertEqual(self.calls, ["turn_off"])

    async def test_night_window_keeps_socket_on(self):
        d = self.device()
        decision = await d.async_run(self.context(12, night=True), -1200)
        self.assertTrue(decision.forced)
        self.assertEqual(self.calls, [])

    async def test_earliest_start_and_standby_detection_still_apply(self):
        d = self.device()
        d.params["earliest_start"] = "17:00"
        self.assertFalse((await d.async_run(self.context(), -1200)).on)
        d = self.device()
        self.values["sensor.load"] = "50"
        decision = await d.async_run(self.context(), -1200)
        self.assertFalse(decision.forced)
        self.assertEqual(d.state["sm"], "erkannt")
        self.assertEqual(self.calls, [])
