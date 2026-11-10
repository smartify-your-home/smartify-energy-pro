"""PV forecast vs actual production: immutable hourly forecast and metered energy.

No cloud or provider calls, no backfill, no counting gaps as zero production.
Hours are keyed by UTC start so DST repeated hours remain distinct.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import isfinite

MAX_GAP_SECONDS = 180
MIN_COVERAGE_SECONDS = 3420  # 95 % of one hour
RETENTION_DAYS = 15  # 14 calendar days plus a safe boundary buffer
MAX_REPORT_HOURS = 14 * 24


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _hour(value: datetime) -> datetime:
    return _utc(value).replace(minute=0, second=0, microsecond=0)


class PVComparison:
    def __init__(self) -> None:
        self.forecasts: dict[str, float] = {}
        self.actual_wh: dict[str, float] = {}
        self.coverage_s: dict[str, float] = {}
        self.previous: tuple[datetime, float] | None = None

    def capture(self, now: datetime, forecast_hours: dict[datetime, float]) -> None:
        """Lock the first observed forecast for future full hours only."""
        now_utc = _utc(now)
        self._prune(now)
        for timestamp, wh in forecast_hours.items():
            if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
                continue
            stamp = _hour(timestamp)
            if stamp <= now_utc:
                continue
            if not isinstance(wh, (int, float)) or not isfinite(wh) or wh < 0:
                continue
            self.forecasts.setdefault(stamp.isoformat(), round(float(wh), 3))

    def observe(self, now: datetime, watts: float | None) -> None:
        """Integrate only continuously observed, valid generation power."""
        now = _utc(now)
        valid = (
            watts is not None and isinstance(watts, (int, float))
            and not isinstance(watts, bool) and isfinite(watts) and watts >= 0
        )
        if valid and self.previous:
            prior_time, prior_watts = self.previous
            elapsed = (now - prior_time).total_seconds()
            if 0 < elapsed <= MAX_GAP_SECONDS:
                cursor = prior_time
                while cursor < now:
                    key_time = _hour(cursor)
                    segment_end = min(now, key_time + timedelta(hours=1))
                    seconds = (segment_end - cursor).total_seconds()
                    key = key_time.isoformat()
                    self.actual_wh[key] = self.actual_wh.get(key, 0.0) + prior_watts * seconds / 3600
                    self.coverage_s[key] = self.coverage_s.get(key, 0.0) + seconds
                    cursor = segment_end
        self.previous = (now, float(watts)) if valid else None
        self._prune(now)

    def _prune(self, now: datetime) -> None:
        cutoff = (_hour(now) - timedelta(days=RETENTION_DAYS)).isoformat()
        ceiling = (_hour(now) + timedelta(days=3)).isoformat()
        for mapping in (self.forecasts, self.actual_wh, self.coverage_s):
            for key in list(mapping):
                if key < cutoff or key > ceiling:
                    del mapping[key]

    def dump(self) -> dict:
        return {
            "forecast": self.forecasts,
            "actual_wh": {k: round(v, 4) for k, v in self.actual_wh.items()},
            "coverage_s": {k: round(v, 2) for k, v in self.coverage_s.items()},
        }

    def restore(self, data: object, now: datetime) -> None:
        if not isinstance(data, dict):
            return
        for key, target in (("forecast", self.forecasts),
                            ("actual_wh", self.actual_wh),
                            ("coverage_s", self.coverage_s)):
            raw = data.get(key)
            if not isinstance(raw, dict):
                continue
            for stamp, value in raw.items():
                try:
                    dt = datetime.fromisoformat(stamp)
                    if dt.tzinfo is None or dt.minute or dt.second or dt.microsecond:
                        continue
                    number = float(value)
                    if isfinite(number) and number >= 0:
                        target[_hour(dt).isoformat()] = number
                except (TypeError, ValueError, OverflowError):
                    continue
        self._prune(now)
        self.previous = None  # Never integrate across a HA restart.

    def recent(self, now: datetime, hours: int = 48) -> dict:
        """Compare historical elapsed hours (including incomplete gaps).

        Every hour is keyed in UTC, so both repeated DST hours are preserved.
        Only complete hours with >=95% valid meter coverage count as actuals.
        """
        now_utc = _utc(now)
        horizon = max(1, min(MAX_REPORT_HOURS, int(hours)))
        current_hour = _hour(now_utc)
        begin = current_hour - timedelta(hours=horizon - 1)
        rows = []
        forecast_kwh = actual_kwh = 0.0
        compared = 0
        for offset in range(horizon):
            stamp = begin + timedelta(hours=offset)
            key = stamp.isoformat()
            expected = self.forecasts.get(key)
            complete = stamp + timedelta(hours=1) <= now_utc
            covered = self.coverage_s.get(key, 0.0) >= MIN_COVERAGE_SECONDS
            valid = complete and covered and expected is not None
            measured = self.actual_wh.get(key)
            rows.append({
                "zeit": key,
                "prognose_wh": round(expected, 1) if expected is not None else None,
                "ist_wh": round(measured, 1) if valid and measured is not None else None,
            })
            if valid and measured is not None:
                compared += 1
                forecast_kwh += expected / 1000
                actual_kwh += measured / 1000
        return {
            "stunden": rows,
            "prognose_kwh": round(forecast_kwh, 2) if compared else None,
            "ist_kwh": round(actual_kwh, 2) if compared else None,
            "abweichung_pct": round((actual_kwh / forecast_kwh - 1) * 100, 1)
            if compared and forecast_kwh > 0 else None,
            "verglichene_stunden": compared,
            "zeitraum_stunden": horizon,
            "hinweis": "Vergleich nur aus vollständig gemessenen und zuvor prognostizierten Stunden.",
        }

    def today(self, now: datetime, tzinfo) -> dict:
        """Backward-compatible calendar-day summary for existing consumers."""
        now_utc = _utc(now)
        day = now_utc.astimezone(tzinfo).date()
        rows = []
        forecast_kwh = actual_kwh = 0.0
        for key in sorted(self.forecasts):
            start = datetime.fromisoformat(key)
            if start.astimezone(tzinfo).date() != day:
                continue
            complete = start + timedelta(hours=1) <= now_utc
            covered = self.coverage_s.get(key, 0.0) >= MIN_COVERAGE_SECONDS
            valid = complete and covered
            expected = self.forecasts[key]
            measured = self.actual_wh.get(key, 0.0)
            rows.append({
                "zeit": key,
                "prognose_wh": round(expected, 1),
                "ist_wh": round(measured, 1) if valid else None,
            })
            if valid:
                forecast_kwh += expected / 1000
                actual_kwh += measured / 1000
        compared = sum(row["ist_wh"] is not None for row in rows)
        return {
            "stunden": rows,
            "prognose_kwh": round(forecast_kwh, 2) if compared else None,
            "ist_kwh": round(actual_kwh, 2) if compared else None,
            "abweichung_pct": round((actual_kwh / forecast_kwh - 1) * 100, 1)
            if compared and forecast_kwh > 0 else None,
            "verglichene_stunden": compared,
            "hinweis": "Nur vollständig gemessene Stunden mit gespeicherter Ursprungsprognose.",
        }
