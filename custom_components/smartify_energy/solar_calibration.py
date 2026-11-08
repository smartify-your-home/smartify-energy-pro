"""Conservative optional feedback calibration for cloud-driven PV forecasts.

Learns only from a real PV production power sensor and forecast values recorded
before the observation. Neither grid power nor battery power is an acceptable
substitute. In-memory observations are sampled at most once per 10 minutes.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from math import isfinite
from typing import Any

BANDS = ("clear", "partial", "overcast")
MIN_PREDICTION_W = 300.0
MIN_SAMPLES = 6
MIN_INTERVAL = timedelta(minutes=10)
MAX_RECORDS = 4500


def cloud_band(cloud: float) -> str:
    """Classify the forecast cloud cover."""
    return "clear" if cloud < 25 else "partial" if cloud < 75 else "overcast"


class SolarCalibration:
    """Bounded weather-stratified adaptation and transparent error history."""

    def __init__(self) -> None:
        self.samples: list[dict[str, Any]] = []
        self.last_observation: datetime | None = None

    def restore(self, data: Any, now: datetime) -> None:
        """Reject corrupt/future/obsolete data; never trust persisted factors."""
        self.samples.clear()
        self.last_observation = None
        if not isinstance(data, list):
            return
        for row in data[-MAX_RECORDS:]:
            if not isinstance(row, dict):
                continue
            try:
                stamp = datetime.fromisoformat(str(row["time"]))
                predicted = float(row["predicted"])
                actual = float(row["actual"])
                cloud = float(row["cloud"])
                if (stamp.tzinfo is None or not now - timedelta(days=30) <= stamp <= now
                        or not all(isfinite(x) for x in (predicted, actual, cloud))
                        or predicted < MIN_PREDICTION_W or actual < 0 or not 0 <= cloud <= 100):
                    continue
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
            self.samples.append({"time": stamp.isoformat(), "predicted": predicted,
                                 "actual": actual, "cloud": cloud})
        self.samples.sort(key=lambda item: item["time"])
        if self.samples:
            self.last_observation = datetime.fromisoformat(self.samples[-1]["time"])

    def dump(self) -> list[dict[str, Any]]:
        return self.samples[-MAX_RECORDS:]

    def reset(self) -> None:
        self.samples.clear()
        self.last_observation = None

    def observe(self, now: datetime, actual: float, predicted: float,
                cloud: float, capacity_w: float) -> bool:
        """Record eligible observations; skip night, spikes and likely clipping.

        No learning is performed from values <=0 for prediction or from sparse
        observations. A prediction must have been captured before this sample.
        """
        if (now.tzinfo is None or not all(isfinite(x) for x in (actual, predicted, cloud, capacity_w))
                or predicted < MIN_PREDICTION_W or actual < 0 or not 0 <= cloud <= 100
                or capacity_w <= 0 or actual > capacity_w * 1.10
                or actual >= capacity_w * 0.98
                or (self.last_observation and now - self.last_observation < MIN_INTERVAL)):
            return False
        self.samples.append({"time": now.isoformat(), "predicted": round(predicted, 2),
                             "actual": round(actual, 2), "cloud": cloud})
        self.last_observation = now
        cutoff = now - timedelta(days=30)
        self.samples = [x for x in self.samples
                        if datetime.fromisoformat(x["time"]) >= cutoff][-MAX_RECORDS:]
        return True

    def factor(self, cloud: float, now: datetime) -> float:
        """Robust weighted correction; shrink toward 1 until data are sufficient."""
        if not isfinite(cloud) or not 0 <= cloud <= 100:
            return 1.0
        band = cloud_band(cloud)
        eligible = [r for r in self.samples
                    if cloud_band(r["cloud"]) == band
                    and timedelta(0) <= now - datetime.fromisoformat(r["time"]) <= timedelta(days=30)]
        if len(eligible) < MIN_SAMPLES:
            return 1.0
        # Bounded ratios prevent one cloud-front outlier dominating the model.
        ratios = sorted(max(0.45, min(1.45, r["actual"] / r["predicted"])) for r in eligible)
        trim = len(ratios) // 10
        selected = ratios[trim:len(ratios) - trim] if trim else ratios
        robust = sum(selected) / len(selected)
        confidence = min(1.0, (len(eligible) - MIN_SAMPLES + 1) / 24)
        return round(max(0.6, min(1.25, 1 + (robust - 1) * confidence)), 4)

    def diagnostics(self, now: datetime) -> dict[str, Any]:
        """7/30-day absolute percentage-independent mean absolute errors in W."""
        out: dict[str, Any] = {"samples": len(self.samples)}
        for band in BANDS:
            out[f"factor_{band}"] = self.factor(
                {"clear": 0, "partial": 50, "overcast": 100}[band], now)
            out[f"samples_{band}"] = sum(1 for r in self.samples
                                         if cloud_band(r["cloud"]) == band)
        for days in (7, 30):
            recent = [r for r in self.samples
                      if timedelta(0) <= now - datetime.fromisoformat(r["time"]) <= timedelta(days=days)]
            out[f"mae_{days}d_w"] = (round(sum(abs(r["actual"] - r["predicted"]) for r in recent)
                                          / len(recent), 1) if recent else None)
            out[f"samples_{days}d"] = len(recent)
        out["last_sample"] = self.last_observation.isoformat() if self.last_observation else None
        return out
