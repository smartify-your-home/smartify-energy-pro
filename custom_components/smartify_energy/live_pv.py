"""Optional, local-only live irradiance estimator for short-range PV forecasts.

Uses *generation* power against an astronomical clear-sky reference, rather
than comparing power to STC peak or grid balance. No external API and no
persistent live samples. Never classifies fog vs overcast as a certainty.
"""
from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
from math import isfinite
from statistics import median, pstdev

from .solar_model import _clear_sky_poa, pv_hours

SAMPLE_WINDOW = timedelta(minutes=30)
MAX_GAP = timedelta(minutes=5)
MIN_SPAN = timedelta(minutes=5)
MAX_SAMPLE_AGE = timedelta(minutes=4)


class LivePVEstimator:
    """30-minute rolling clear-sky index and conservative 2h correction."""

    def __init__(self, latitude: float, longitude: float, surfaces: list[dict]) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.surfaces = surfaces
        self.capacity = sum(float(s.get("kwp") or 0) for s in surfaces) * 1000
        self.samples: deque[tuple[datetime, float]] = deque(maxlen=90)
        self.state = "learning"
        self.index: float | None = None
        self.trend: float | None = None
        self.volatility: float | None = None
        self.last_sample: datetime | None = None

    def clear_power(self, now: datetime) -> float:
        total = 0.0
        for s in self.surfaces[:4]:
            kwp = float(s.get("kwp") or 0)
            if kwp <= 0:
                continue
            tilt, az = float(s.get("tilt") or 0), float(s.get("azimuth", 180))
            poa = _clear_sky_poa(now, self.latitude, self.longitude, tilt, az)
            bifaciality = float(s.get("bifaciality") or 0)
            if 0 < bifaciality <= 1:
                poa += bifaciality * _clear_sky_poa(
                    now, self.latitude, self.longitude, 180 - tilt, (az + 180) % 360)
            total += kwp * poa * 0.85
        return total

    def observe(self, now: datetime, watts: float | None) -> bool:
        """Returns True if a valid new sample is accepted."""
        if not (now.tzinfo and self.capacity > 0 and isinstance(watts, (int, float))
                and not isinstance(watts, bool) and isfinite(watts)
                and 0 <= watts < self.capacity * 0.98):
            return False
        reference = self.clear_power(now)
        if reference < 350 or reference > self.capacity * 1.10:
            return False
        ratio = max(0.0, min(1.3, watts / reference))
        if self.samples and now <= self.samples[-1][0]:
            return False
        if self.samples and (now - self.samples[-1][0]).total_seconds() < 25:
            return False
        if self.samples and now - self.samples[-1][0] > MAX_GAP:
            self.samples.clear()
        self.samples.append((now, ratio))
        self.last_sample = now
        while self.samples and now - self.samples[0][0] > SAMPLE_WINDOW:
            self.samples.popleft()
        if len(self.samples) < 6 or now - self.samples[0][0] < MIN_SPAN:
            self.state = "learning"
            return True
        values = [v for _, v in self.samples]
        self.index = median(values[-min(10, len(values)):])
        self.trend = median(values[-3:]) - median(values[:3])
        self.volatility = pstdev(values) / max(0.1, median(values))
        if self.trend > 0.17 and all(b >= a - 0.04 for a, b in zip(values, values[1:])):
            self.state = "clearing"
        elif self.trend < -0.17 and all(b <= a + 0.04 for a, b in zip(values, values[1:])):
            self.state = "dimming"
        elif self.volatility > 0.20:
            self.state = "variable"
        elif self.index >= 0.70:
            self.state = "clear"
        elif self.index < 0.43:
            self.state = "low_irradiance"
        else:
            self.state = "partial"
        return True

    def corrected(self, now: datetime, base_hours: dict[datetime, float]) -> dict[datetime, float]:
        """Blend near-term live radiation into the base without changing history.

        A missing, stale, clipped or unreliable measurement always yields the
        original prediction. Modifies at most the current and next two hours.
        """
        result = dict(base_hours)
        if (self.index is None or self.state == "learning" or not self.last_sample
                or now - self.last_sample > MAX_SAMPLE_AGE or self.volatility is None
                or self.volatility > 0.5):
            return result
        hour_now = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        clear = pv_hours(now, self.latitude, self.longitude, self.surfaces,
                         {h: 0.0 for h in base_hours})
        quality = 0.25 if self.state == "variable" else 0.65
        for hour, original in base_hours.items():
            offset = (hour.astimezone(UTC) - hour_now).total_seconds() / 3600
            if not 0 <= offset < 3 or original <= 0:
                continue
            weight = quality * max(0.0, 1 - offset / 2.25)
            if weight <= 0:
                continue
            target = clear.get(hour, 0.0) * min(1.15, self.index)
            mixed = original * (1 - weight) + target * weight
            cap = max(0.0, min(self.capacity, clear.get(hour, 0.0) * 1.15))
            result[hour] = round(max(0.0, min(cap, original * 1.8, max(original * 0.55, mixed))), 2)
        return result

    def diagnostics(self, now: datetime) -> dict:
        ready = (self.index is not None and self.last_sample is not None
                 and now - self.last_sample <= MAX_SAMPLE_AGE
                 and self.state != "learning")
        return {"state": self.state if ready else "insufficient_data",
                "index_pct": round(self.index * 100, 1) if ready else None,
                "trend_pct": round(self.trend * 100, 1) if ready and self.trend is not None else None,
                "volatility_pct": round(self.volatility * 100, 1) if ready else None,
                "samples": len(self.samples),
                "last_sample": self.last_sample.isoformat() if self.last_sample else None,
                "horizon_hours": 2}
