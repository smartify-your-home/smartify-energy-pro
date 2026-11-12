"""Read-only PV everyday advice based on complete local forecast hours.

No actuator writes, API calls, assumed zeroes or hidden consumption claims.
The advice is informational and may change with the weather forecast.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from math import isfinite

START_HOUR = 8
END_HOUR = 16
MIN_RELATIVE_ADVANTAGE = 0.25
MIN_ABSOLUTE_ADVANTAGE_WH = 3000


def day_windows(hours: dict[datetime, float], now: datetime) -> list[dict]:
    """Summarize only complete local 08:00–16:00 forecast windows."""
    indexed = {k.astimezone(now.tzinfo): v for k, v in hours.items()
               if isinstance(k, datetime) and k.tzinfo is not None}
    results = []
    for offset in range(3):
        date = now.date() + timedelta(days=offset)
        stamps = [datetime.combine(date, time(h), now.tzinfo) for h in range(START_HOUR, END_HOUR)]
        values = [indexed.get(stamp) for stamp in stamps]
        complete = all(isinstance(v, (float, int)) and isfinite(v) and v >= 0 for v in values)
        results.append({"tag": ("heute", "morgen", "uebermorgen")[offset],
                        "datum": date.isoformat(), "vollstaendig": complete,
                        "kwh": round(sum(values) / 1000, 2) if complete else None,
                        "stunden": values if complete else []})
    return results


def _prefer_later(first: dict, other: dict) -> bool:
    a, b = first.get("kwh"), other.get("kwh")
    if a is None or b is None:
        return False
    return b - a >= MIN_ABSOLUTE_ADVANTAGE_WH / 1000 and (
        (a <= 0 and b >= MIN_ABSOLUTE_ADVANTAGE_WH / 1000) or
        (a > 0 and b >= a * (1 + MIN_RELATIVE_ADVANTAGE))
    )


def _recommend_day(days: list[dict]) -> dict | None:
    """Recommend the next useful day; only postpone twice for another clear gain."""
    valid = [day for day in days if day["vollstaendig"]]
    if not valid:
        return None
    first = valid[0]
    later = next((day for day in valid[1:] if _prefer_later(first, day)), None)
    if later is not None:
        last = valid[-1]
        if last is not later and _prefer_later(later, last):
            later = last
        return {"tag": later["tag"], "base_tag": first["tag"],
                "mehrertrag_kwh": round(later["kwh"] - first["kwh"], 2),
                "mehrertrag_prozent": round((later["kwh"] / first["kwh"] - 1) * 100, 1)
                if first["kwh"] else None}
    return {"tag": first["tag"], "base_tag": first["tag"],
            "mehrertrag_kwh": 0, "mehrertrag_prozent": 0}


def _tip(key: str, icon: str, title: str, detail: str, priority: int, **attrs) -> dict:
    return {"typ": key, "icon": icon, "text": title, "detail": detail,
            "prioritaet": priority, **attrs}


def _best_start(day: dict, duration: float, nominal_w: float, base_load_w: float) -> tuple[int, float] | None:
    """Highest PV-supported contiguous run inside the 08–16 h window."""
    if not day["vollstaendig"] or not 0 < duration <= 8:
        return None
    hours = day["stunden"]
    n = max(1, min(8, int(duration + 0.999)))
    options = []
    for offset in range(9 - n):
        supported = sum(max(0.0, min(nominal_w, watts - base_load_w)) for watts in hours[offset:offset + n])
        options.append((START_HOUR + offset, supported / 1000))
    return max(options, key=lambda x: x[1], default=None)


def build_advice(hours: dict[datetime, float], now: datetime, devices: list[dict] | None = None,
                 *, base_load_w: float = 400, live_state: str | None = None,
                 battery_soc: float | None = None, battery_capacity_kwh: float = 0) -> dict:
    """Return compact ranked tips, a dedicated laundry tip and honest day totals.

    Only configured devices generate device-specific messages. Missing full
    8-hour windows never count as zero. No direct impact on device dispatch.
    """
    if now.tzinfo is None:
        raise ValueError("Timezone-aware local time required")
    days = day_windows(hours, now)
    if now.hour < 6:
        return {"state": "ab_06_uhr", "tips": [], "waschtipp": None,
                "tage": days, "zeitfenster": "08:00–16:00", "aktualisiert": now.isoformat()}
    devices = [d for d in (devices or []) if d.get("mode") != "off"]
    comparison = _recommend_day(days)
    tips = []
    laundry = None
    first = next((d for d in devices if d.get("kind") == "washing_machine"), None)
    if first:
        if comparison:
            wanted = comparison["tag"]
            title = "Wäsche " + ("heute waschen" if wanted == "heute" else
                                  "besser morgen waschen" if wanted == "morgen" else
                                  "besser übermorgen waschen")
            details = ("08–16 Uhr · " + 
                       (f"+{comparison['mehrertrag_kwh']:.1f} kWh"
                        if comparison["mehrertrag_kwh"] else "kein deutlicher Vorteil"))
            if comparison["mehrertrag_prozent"] and comparison["mehrertrag_kwh"]:
                details += f" (+{comparison['mehrertrag_prozent']:.0f} %)"
            laundry = _tip("waschen", "mdi:washing-machine", title, details, 10,
                           empfehlung=comparison["tag"], **comparison)
            tips.append(laundry)
        else:
            laundry = _tip("waschen", "mdi:washing-machine", "Noch keine vollständige PV-Prognose",
                           "08–16 Uhr · Daten fehlen", 90, empfehlung="unbekannt")
    applicable = [d for d in devices if d.get("kind") in {"dishwasher", "dryer"}]
    for device in applicable:
        duration = float(device.get("duration") or 2)
        nominal = float(device.get("power") or 1800)
        if not (nominal > 0 and 0 < duration <= 8):
            continue
        options = [(day, start) for day in days if (start := _best_start(day, duration, nominal, base_load_w))]
        if not options:
            continue
        best_day, (hour, energy) = max(options, key=lambda entry: entry[1][1])
        first_day, (_, baseline_energy) = options[0]
        if best_day["tag"] != first_day["tag"] and (
            energy < baseline_energy * 1.25 or energy - baseline_energy < 0.5
        ):
            best_day, (hour, energy) = options[0]
        appliance_name = "Geschirrspüler" if device["kind"] == "dishwasher" else "Trockner"
        when = best_day["tag"].replace("uebermorgen", "übermorgen")
        tips.append(_tip(device["kind"], "mdi:dishwasher" if device["kind"] == "dishwasher"
                         else "mdi:tumble-dryer", f"{appliance_name} {when} ab {hour:02d} Uhr",
                         f"{hour:02d}–{min(24, hour + int(duration + 0.999)):02d} Uhr · "
                         f"ca. {energy:.1f} kWh PV-Potenzial", 20,
                         tag=best_day["tag"], start=f"{hour:02d}:00"))
    if any(d.get("kind") == "ev" and d.get("pv_only", True) for d in devices) and comparison:
        tag = comparison["tag"]
        if tag != "heute" and comparison["mehrertrag_kwh"] >= 3:
            tips.append(_tip("e_auto", "mdi:ev-station",
                             f"E-Auto besser {tag.replace('uebermorgen','übermorgen')} laden",
                             f"08–16 Uhr · +{comparison['mehrertrag_kwh']:.1f} kWh PV-Prognose",
                             25, tag=tag))
    if any(d.get("kind") in {"heatpump", "heater"} for d in devices) and comparison:
        if comparison["tag"] == "morgen":
            tips.append(_tip("warmwasser", "mdi:water-boiler",
                             "Warmwasser morgen bevorzugen",
                             "08–16 Uhr · höherer PV-Ertrag erwartet", 35, tag="morgen"))
    if battery_capacity_kwh > 0 and battery_soc is not None and 0 <= battery_soc <= 100:
        available = next((day for day in days if day["vollstaendig"]), None)
        if available:
            need = battery_capacity_kwh * (100 - battery_soc) / 100
            if need >= 0.5 and available["kwh"] >= need + base_load_w * 8 / 1000:
                tips.append(_tip("speicher", "mdi:home-battery",
                                 "PV könnte den Speicher heute füllen" if available["tag"] == "heute"
                                 else "PV-Potenzial für Speicherladung",
                                 f"{available['kwh']:.1f} kWh im Zeitfenster erwartet",
                                 45, tag=available["tag"]))
    if live_state in {"clearing", "variable"}:
        title = ("Sonne setzt sich durch" if live_state == "clearing"
                 else "Wechselnde Einstrahlung")
        desc = ("PV-Erzeugung steigt gegenüber der Klarhimmel-Referenz"
                if live_state == "clearing" else
                "Kurzfristprognose unsicher – Verbrauchsstarts vorsichtig planen")
        tips.append(_tip("pv_wetter", "mdi:weather-partly-cloudy", title, desc,
                         15 if live_state == "clearing" else 50))
    tips.sort(key=lambda x: x["prioritaet"])
    return {"state": tips[0]["text"] if tips else "Kein PV-Tipp verfügbar",
            "tips": tips, "waschtipp": laundry, "tage": [
                {k: v for k, v in day.items() if k != "stunden"} for day in days],
            "zeitfenster": "08:00–16:00", "aktualisiert": now.isoformat(),
            "mindestens_mehrertrag_kwh": 3, "mindestens_mehrertrag_prozent": 25}
