"""Privacy-preserving config-entry diagnostics."""
from dataclasses import asdict

from homeassistant.components.diagnostics import async_redact_data

from .const import DOMAIN
from .devices.base import ENTITY_FIELDS


async def async_get_config_entry_diagnostics(hass, entry):
    """No names, entity IDs, URLs, raw config, tokens or free-form reasons."""
    manager = entry.runtime_data
    devices = []
    for dev in manager.devices.values():
        decision = dev.last_decision
        devices.append({
            "type": dev.TYPE, "parameters": dict(dev.params), "status": dev.status,
            "configured_inputs": [key for key in ENTITY_FIELDS.get(dev.TYPE, ()) if dev.cfg.get(key)],
            "decision": {k: v for k, v in asdict(decision).items() if k != "reason"} if decision else None,
            "budget": manager.device_budgets.get(dev.id, {}),
        })
    return async_redact_data({
        "domain": DOMAIN, "hub_parameters": dict(manager.params), "devices": devices,
        "budget": {"now_w": manager.budget_now, "average_w": manager.budget_avg,
                   "allocated_w": manager.allocated},
        "budget_history": [{"time": ts.isoformat(), "watts": value}
                           for ts, value in list(manager._history)[-240:]],
        "forecast": {"configured": manager.forecast.configured,
                     "hours": len(manager.forecast.hours),
                     "last_refresh": manager.forecast.last_update.isoformat() if manager.forecast.last_update else None,
                     "has_error": bool(manager.forecast.error)},
    }, {"name", "entity_id", "token", "password", "api_key"})
