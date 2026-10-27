"""Stable status codes; legacy phase names remain compatible in storage."""
STATUS_CODES = {
    "init": "initializing", "bereit": "ready", "erkannt": "detected", "wartet": "waiting",
    "laeuft": "running", "fertig": "finished", "aus": "off", "manuell": "manual",
    "beobachten": "observing", "inaktiv": "inactive", "sperrzeit": "locked",
    "max_erreicht": "limit_reached", "nicht_verbunden": "disconnected", "voll": "full",
    "laedt_sofort": "charging_now", "laedt_pflicht": "charging_required", "laedt_pv": "charging_pv",
    "boost": "boost", "actuator_unavailable": "actuator_unavailable", "actuator_error": "actuator_error",
}
STATUS_OPTIONS = list(dict.fromkeys(STATUS_CODES.values()))
