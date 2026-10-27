"""Finished household appliances reset automatically on the next program start."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

from test_load_budget import Context, DryerDevice, LoadDevice


class AutoResetTests(unittest.TestCase):
    def make(self, cls=LoadDevice, sensor=True, **cfg):
        self.values = {"switch.dev": "on", "sensor.dev": "2"}

        def get(entity):
            value = self.values.get(entity)
            return NS(state=value, attributes={"unit_of_measurement": "W"}) if value is not None else None

        manager = NS(hass=NS(states=NS(get=get)), hub_mode="auto", async_param_changed=lambda: None)
        config = {"switch": "switch.dev", **cfg}
        if sensor:
            config["power_sensor"] = "sensor.dev"
        dev = cls(manager, "dev", "Gerät", config)
        dev.params.update(mode="auto", min_surplus=1500, latest_start="23:59")
        dev.state["sm"] = "fertig"
        return dev

    def ctx(self, now):
        return Context(now, 30, 0, 0, 0, True, False, 0, [])

    def test_standby_stays_finished(self):
        dev = self.make()
        now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
        for s in range(0, 30, 5):
            dev.decide(self.ctx(now + timedelta(seconds=s)), 0)
        self.assertEqual(dev.state["sm"], "fertig")

    def test_new_program_resets_without_button(self):
        dev = self.make()
        now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
        self.values["sensor.dev"] = "40"
        dev.decide(self.ctx(now), 0)
        self.assertEqual(dev.state["sm"], "fertig")
        dev.decide(self.ctx(now + timedelta(seconds=6)), 0)
        self.assertEqual(dev.state["sm"], "erkannt")

    def test_short_spike_does_not_reset(self):
        dev = self.make()
        now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
        self.values["sensor.dev"] = "40"
        dev.decide(self.ctx(now), 0)
        self.values["sensor.dev"] = "2"
        dev.decide(self.ctx(now + timedelta(seconds=3)), 0)
        self.values["sensor.dev"] = "40"
        dev.decide(self.ctx(now + timedelta(seconds=6)), 0)
        self.assertEqual(dev.state["sm"], "fertig")

    def test_without_sensor_requires_plug_off_on(self):
        dev = self.make(sensor=False)
        now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
        dev.decide(self.ctx(now), 0)
        self.assertEqual(dev.state["sm"], "fertig")
        self.values["switch.dev"] = "off"
        dev.decide(self.ctx(now + timedelta(seconds=10)), 0)
        self.values["switch.dev"] = "on"
        dev.decide(self.ctx(now + timedelta(seconds=20)), 0)
        self.assertNotEqual(dev.state["sm"], "fertig")

    def test_non_resumable_dryer_resets_to_running(self):
        dev = self.make(DryerDevice)
        now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
        self.values["sensor.dev"] = "900"
        dev.decide(self.ctx(now), 0)
        dev.decide(self.ctx(now + timedelta(seconds=6)), 0)
        self.assertEqual(dev.state["sm"], "laeuft")


if __name__ == "__main__":
    unittest.main()
