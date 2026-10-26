"""Strict rolling forecast window for optional boost start checks (Wh)."""
from datetime import timedelta, timezone
import math


def rolling_energy(provider, now, hours):
    """Return (Wh, error); require fresh, complete hourly data, including zeros."""
    if provider is None or not provider.configured:
        return None, "Keine PV-Prognosequelle konfiguriert"
    if provider.error:
        return None, "PV-Prognose meldet einen Fehler"
    updated = provider.last_update
    if updated is None or updated.tzinfo is None:
        return None, "PV-Prognose noch nicht verfügbar"
    start = now.astimezone(timezone.utc)
    age = (start - updated.astimezone(timezone.utc)).total_seconds()
    if not 0 <= age <= 3600:
        return None, "PV-Prognose veraltet (älter als 60 Minuten)"
    end = start + timedelta(hours=hours)
    intervals = []
    for stamp, raw in provider.hours.items():
        if stamp.tzinfo is None:
            continue
        left = stamp.astimezone(timezone.utc)
        right = left + timedelta(hours=1)
        if right <= start or left >= end:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None, "PV-Prognose enthält ungültige Stundenwerte"
        if not math.isfinite(value) or value < 0:
            return None, "PV-Prognose enthält ungültige Stundenwerte"
        intervals.append((max(left, start), min(right, end), value))
    cursor, total = start, 0.0
    for left, right, value in sorted(intervals):
        if left != cursor:
            return None, "PV-Prognose deckt das Zeitfenster nicht vollständig ab"
        total += value * (right - left).total_seconds() / 3600
        cursor = right
    if cursor != end:
        return None, "PV-Prognose deckt das Zeitfenster nicht vollständig ab"
    return total, None
