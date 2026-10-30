"""Regression tests for configurable residual heating reservation."""
from types import SimpleNamespace

import pytest

from custom_components.smartify_energy.budget import additional_reservation
from custom_components.smartify_energy.devices import base as base_module
from custom_components.smartify_energy.devices import load as load_module
from custom_components.smartify_energy.devices.dryer import DryerDevice
from custom_components.smartify_energy.devices.load import LoadDevice, RUNNING


@pytest.fixture
def appliance(monkeypatch):
    manager = SimpleNamespace(
        hass=SimpleNamespace(states=SimpleNamespace(get=lambda _entity: SimpleNamespace(state="on"))),
        hub_mode="auto",
    )
    dev = LoadDevice(
        manager, "gs", "Geschirrspüler",
        {"switch": "switch.gs", "power_sensor": "sensor.gs", "nominal_power": 2000},
    )
    dev.state.update(sm=RUNNING, approved=True)
    measured = {"value": 100.0}
    monkeypatch.setattr(load_module, "power_w", lambda _hass, _entity: measured["value"])
    monkeypatch.setattr(base_module, "power_w", lambda _hass, _entity: measured["value"])
    return dev, measured


def test_default_is_full_reservation(appliance):
    dev, measured = appliance
    dev.state["hp_done"] = True
    assert dev.p("pause_reservation_pct") == 100
    assert dev.reserved_power == 2000
    assert additional_reservation(dev.reserved_power, measured["value"], 0) == 1900


def test_half_reservation_only_after_first_heating_phase(appliance):
    dev, measured = appliance
    dev.params["pause_reservation_pct"] = 50
    assert dev.reserved_power == 2000  # before first completed heating phase
    dev.state["hp_done"] = True
    assert dev.reserved_power == 1000
    assert additional_reservation(dev.reserved_power, measured["value"], 0) == 900
    measured["value"] = 2100
    assert dev.reserved_power == 2100  # actual heating draw wins
    measured["value"] = 100
    assert dev.reserved_power == 1000


def test_zero_reservation_and_sensor_failure(appliance):
    dev, measured = appliance
    dev.params["pause_reservation_pct"] = 0
    dev.state["hp_done"] = True
    assert dev.reserved_power == 100
    measured["value"] = None
    assert dev.reserved_power == 2000  # no phantom surplus if meter is unavailable


def test_dryer_keeps_full_reservation(monkeypatch):
    manager = SimpleNamespace(hass=SimpleNamespace(), hub_mode="auto")
    dev = DryerDevice(
        manager, "dryer", "Trockner",
        {"switch": "switch.dryer", "power_sensor": "sensor.dryer",
         "nominal_power": 2000, "dryer_resume": "yes"},
    )
    dev.state.update(sm=RUNNING, approved=True, hp_done=True)
    monkeypatch.setattr(load_module, "power_w", lambda _hass, _entity: 100.0)
    monkeypatch.setattr(base_module, "power_w", lambda _hass, _entity: 100.0)
    assert dev.reserved_power == 2000
