"""Basis für Parameter-Entities (number/select/switch/time)."""
from __future__ import annotations

from homeassistant.const import EntityCategory

from .devices import BaseDevice
from .entity import SmartifyEntity
from .helpers import ParamSpec


def param_specs(owner, platform: str) -> list[ParamSpec]:
    specs = owner.all_param_specs() if isinstance(owner, BaseDevice) else owner.param_specs()
    return [s for s in specs if s.platform == platform]


class ParamEntity(SmartifyEntity):
    def __init__(self, manager, owner, spec: ParamSpec) -> None:
        super().__init__(manager, owner, spec.key)
        self.spec = spec
        self._attr_icon = spec.icon
        if spec.config:
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def value(self):
        return self.owner.p(self.spec.key)

    def set_value(self, value) -> None:
        self.owner.set_param(self.spec.key, value)
        self.async_write_ha_state()
