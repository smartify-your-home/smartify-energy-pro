"""Sensoren."""
from __future__ import annotations

from copy import deepcopy
from time import monotonic
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartifyEntity, add_entities_per_owner
from .helpers import SensorSpec
from .status import STATUS_OPTIONS


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    manager = entry.runtime_data
    add_entities_per_owner(
        manager, async_add_entities,
        lambda owner: [SmartifySensor(manager, owner, s) for s in owner.sensor_specs()],
    )


class SmartifySensor(SmartifyEntity, SensorEntity):
    # Keep live detail for dashboards, but never duplicate it in Recorder.
    _unrecorded_attributes = frozenset({
        "aktuell_w", "mittel_w", "vorreservierung_w", "benoetigt_w", "zusaetzlich_reserviert_w",
        "geraete", "stunden", "grund", "reason", "empfehlung", "boost_startbedingungen",
        "pv_forecast_startbedingung", "ww_aktiv_seit_min", "startsperre_rest_min",
        "netzsaldo_w", "ruecknehmbar_w", "senken_nur_information_w", "speicher_w",
    })

    def __init__(self, manager, owner, spec: SensorSpec) -> None:
        super().__init__(manager, owner, spec.key)
        self.spec = spec
        self._last_publish_time = float("-inf")
        self._last_sensor_snapshot = None
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = SensorDeviceClass(spec.device_class) if spec.device_class else None
        self._attr_state_class = SensorStateClass(spec.state_class) if spec.state_class else None
        self._attr_icon = spec.icon
        if spec.key == "status":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = STATUS_OPTIONS
        if spec.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @callback
    def _handle_update(self) -> None:
        snapshot = (self.native_value, self.extra_state_attributes, self.available)
        if snapshot == self._last_sensor_snapshot:
            return
        now = monotonic()
        old = self._last_sensor_snapshot
        immediate = old is None or snapshot[2] != old[2] or (
            self._key == "status" and snapshot[0] != old[0])
        # Live power at most once per second; changing detail at most every 5 s.
        interval = 1 if self.spec.unit == "W" else 5
        if not immediate and now - self._last_publish_time < interval:
            return
        self._last_publish_time = now
        self._last_sensor_snapshot = deepcopy(snapshot)
        super()._handle_update()

    @property
    def native_value(self) -> Any:
        return self.spec.value()

    @property
    def extra_state_attributes(self) -> dict | None:
        return self.spec.attrs() if self.spec.attrs else None
