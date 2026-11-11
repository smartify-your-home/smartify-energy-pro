"""Fertig-Ansage und 30-Minuten-Erinnerung der Haushaltsgeräte.

Run: python -m unittest discover -s tests
"""
import importlib.util
import sys
import types
import unittest
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch

from test_load_budget import ROOT, DryerDevice, LoadDevice


def _load_announce():
    """Load announce.py with its helpers, without a Home Assistant install."""
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    package = types.ModuleType("sep_announce_test")
    package.__path__ = [str(ROOT)]
    with patch.dict(sys.modules, {
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.core": core,
        "sep_announce_test": package,
    }):
        loaded = {}
        for name in ("helpers", "announce"):
            fullname = "sep_announce_test." + name
            spec = importlib.util.spec_from_file_location(fullname, ROOT / f"{name}.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[fullname] = module
            spec.loader.exec_module(module)
            loaded[name] = module
        return loaded["announce"]


announce = _load_announce()
T0 = datetime(2026, 11, 11, 10, 0, tzinfo=timezone.utc)


class AnnounceBase(unittest.TestCase):
    def setUp(self):
        self.values = {"switch.wm": "on", "sensor.wm": "0"}
        self.sent = []
        self.allow = True

        def get(ent):
            v = self.values.get(ent)
            return NS(state=v, attributes={"unit_of_measurement": "W"}) if v is not None else None

        def send(device, kind, now):
            if not self.allow:
                return False
            self.sent.append((device.name, kind))
            return True

        self.manager = NS(hass=NS(states=NS(get=get)), hub_mode="auto",
                          async_param_changed=lambda *a, **k: None,
                          async_request_run=AsyncMock(), device_budgets={}, announce=send)

    def device(self, cls=LoadDevice, **cfg):
        dev = cls(self.manager, "wm", "Waschmaschine", {
            "switch": "switch.wm", "power_sensor": "sensor.wm", "nominal_power": 2000, **cfg})
        dev.params["mode"] = "auto"
        return dev

    def ctx(self, minutes=0.0):
        return NS(now=T0 + timedelta(minutes=minutes), dt=30)

    def finish(self, dev, minutes=0.0):
        """Run a released program into the finished state at T0 + minutes."""
        dev.state.update(sm="laeuft", approved=True)
        dev._low_since = T0 + timedelta(minutes=minutes) - timedelta(minutes=5)
        dev.pre_update(self.ctx(minutes))
        self.assertEqual(dev.state["sm"], "fertig")


class FinishedAnnouncement(AnnounceBase):
    def test_disabled_by_default(self):
        dev = self.device()
        self.assertFalse(dev.p("announce_finished"))
        self.finish(dev)
        dev.pre_update(self.ctx(45))
        self.assertEqual(self.sent, [])

    def test_announces_once_without_reminder(self):
        dev = self.device()
        dev.params["announce_finished"] = True
        self.finish(dev)
        for minutes in (1, 31, 61, 180):
            dev.pre_update(self.ctx(minutes))
        self.assertEqual(self.sent, [("Waschmaschine", "finished")])

    def test_reminder_every_30_minutes(self):
        dev = self.device()
        dev.params.update(announce_finished=True, announce_reminder=True)
        self.finish(dev)
        for minutes in (10, 29.5, 30, 45, 59.5, 60, 90):
            dev.pre_update(self.ctx(minutes))
        self.assertEqual([kind for _, kind in self.sent],
                         ["finished", "reminder", "reminder", "reminder"])

    def test_reminder_needs_finished_announcement_switch(self):
        dev = self.device()
        dev.params.update(announce_finished=False, announce_reminder=True)
        self.finish(dev)
        dev.pre_update(self.ctx(90))
        self.assertEqual(self.sent, [])

    def test_reset_ends_reminders(self):
        dev = self.device()
        dev.params.update(announce_finished=True, announce_reminder=True)
        self.finish(dev)
        dev._reset()
        dev.pre_update(self.ctx(120))
        self.assertEqual(self.sent, [("Waschmaschine", "finished")])
        self.assertFalse(dev.state["announced"])

    def test_next_program_announces_again(self):
        dev = self.device()
        dev.params["announce_finished"] = True
        self.finish(dev)
        dev._reset()
        self.finish(dev, minutes=200)
        self.assertEqual([kind for _, kind in self.sent], ["finished", "finished"])

    def test_rejected_announcement_is_retried(self):
        """Outside the hub's time window nothing is marked as announced."""
        dev = self.device()
        dev.params.update(announce_finished=True, announce_reminder=True)
        self.allow = False
        self.finish(dev)
        dev.pre_update(self.ctx(40))
        self.assertEqual(self.sent, [])
        self.assertFalse(dev.state.get("announced"))
        self.allow = True
        dev.pre_update(self.ctx(41))
        self.assertEqual([kind for _, kind in self.sent], ["finished"])
        dev.pre_update(self.ctx(71))
        self.assertEqual([kind for _, kind in self.sent], ["finished", "reminder"])

    def test_state_survives_restart_without_second_announcement(self):
        dev = self.device()
        dev.params.update(announce_finished=True, announce_reminder=True)
        self.finish(dev)
        restored = self.device()
        restored.load(dev.dump())
        restored.pre_update(self.ctx(5))
        self.assertEqual([kind for _, kind in self.sent], ["finished"])
        restored.pre_update(self.ctx(30))
        self.assertEqual([kind for _, kind in self.sent], ["finished", "reminder"])

    def test_manager_without_announce_support_is_ignored(self):
        del self.manager.announce
        dev = self.device()
        dev.params["announce_finished"] = True
        self.finish(dev)
        self.assertEqual(dev.state["sm"], "fertig")

    def test_non_resumable_dryer_offers_and_uses_announcement(self):
        dryer = self.device(DryerDevice, dryer_resume="never", duration=2.5)
        keys = [s.key for s in dryer.param_specs()]
        self.assertIn("announce_finished", keys)
        self.assertIn("announce_reminder", keys)
        dryer.params["announce_finished"] = True
        self.finish(dryer)
        self.assertEqual(self.sent, [("Waschmaschine", "finished")])


class AnnounceHelpers(unittest.TestCase):
    def test_texts_follow_language(self):
        self.assertEqual(announce.announce_text("finished", "Trockner", "de"), "Trockner ist fertig.")
        self.assertEqual(announce.announce_text("reminder", "Trockner", "de-AT"),
                         "Trockner ist fertig – bitte ausräumen.")
        self.assertEqual(announce.announce_text("finished", "Dryer", "en"), "Dryer has finished.")
        self.assertEqual(announce.announce_text("finished", "Dryer", "fr"), "Dryer has finished.")

    def test_window(self):
        at = lambda h: datetime(2026, 11, 11, h, 0)  # noqa: E731
        self.assertTrue(announce.announce_window_open(at(12), time(7), time(22)))
        self.assertFalse(announce.announce_window_open(at(23), time(7), time(22)))
        self.assertFalse(announce.announce_window_open(at(6), time(7), time(22)))
        self.assertTrue(announce.announce_window_open(at(3), time(0), time(0)))
        self.assertTrue(announce.announce_window_open(at(23), time(22), time(6)))


if __name__ == "__main__":
    unittest.main()
