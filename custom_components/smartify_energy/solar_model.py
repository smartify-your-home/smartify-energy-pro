"""Estimated PV hourly production for up to four separate roof planes.

Uses HA location, STC kWp, tilt (0=flat) and azimuth (0=N, 90=E,
180=S, 270=W). A lightweight clear-sky plane-of-array approximation is
attenuated by the Meteonomiqs hourly cloud cover; this is not a bankable
irradiance simulation and requires measured PV feedback for calibration.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import asin, cos, degrees, exp, pi, radians, sin
from typing import Any


def hourly_clouds(attributes: dict, now: datetime) -> dict[datetime, float]:
    """Read timestamped cloud values; reject invalid and stale forecast slots."""
    result = {}
    for row in attributes.get("forecast", []) if isinstance(attributes.get("forecast"), list) else []:
        if not isinstance(row, dict):
            continue
        try:
            stamp = datetime.fromisoformat(str(row["datetime"]).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                continue
            stamp = stamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
            cloud = row.get("cloud_coverage")
            if isinstance(cloud, bool) or not isinstance(cloud, (float, int)) or not 0 <= cloud <= 100:
                continue
            if now.astimezone(UTC) - timedelta(hours=1) <= stamp < now.astimezone(UTC) + timedelta(hours=9):
                result[stamp] = float(cloud)
        except (ValueError, KeyError, TypeError):
            continue
    return result


def _clear_sky_poa(stamp: datetime, latitude: float, longitude: float, tilt: float, azimuth: float) -> float:
    """Approximate POA irradiation (W/m²) at a UTC instant.

    Geometry: NOAA fractional year, equation of time and solar declination;
    direct irradiance via simple air-mass attenuation, diffuse isotropic sky.
    """
    t = stamp.astimezone(UTC)
    day = t.timetuple().tm_yday
    hour = t.hour + t.minute / 60
    gamma = 2 * pi / 365 * (day - 1 + (hour - 12) / 24)
    eq = 229.18 * (0.000075 + 0.001868 * cos(gamma) - 0.032077 * sin(gamma)
                   - 0.014615 * cos(2 * gamma) - 0.040849 * sin(2 * gamma))
    decl = (0.006918 - 0.399912 * cos(gamma) + 0.070257 * sin(gamma)
            - 0.006758 * cos(2 * gamma) + 0.000907 * sin(2 * gamma)
            - 0.002697 * cos(3 * gamma) + 0.00148 * sin(3 * gamma))
    phi = radians(latitude)
    hour_angle = radians((hour * 60 + eq + 4 * longitude) / 4 - 180)
    elevation_sin = sin(phi) * sin(decl) + cos(phi) * cos(decl) * cos(hour_angle)
    if elevation_sin <= 0:
        return 0.0
    # Solar vector in ENU axes; panel normal for azimuth from north clockwise.
    east = -cos(decl) * sin(hour_angle)
    north = cos(phi) * sin(decl) - sin(phi) * cos(decl) * cos(hour_angle)
    up = elevation_sin
    beta = radians(tilt)
    az = radians(azimuth)
    incident = max(0.0, east * sin(beta) * sin(az)
                   + north * sin(beta) * cos(az) + up * cos(beta))
    altitude = degrees(asin(max(-1.0, min(1.0, up))))
    air_mass = 1 / (up + 0.50572 * (altitude + 6.07995) ** -1.6364)
    dni = 1000 * exp(-0.14 * air_mass)
    # Diffuse contribution matters especially on cloudy/north-facing roofs.
    dhi = 110 * up
    ghi = dni * up + dhi
    poa = dni * incident + dhi * (1 + cos(beta)) / 2 + 0.2 * ghi * (1 - cos(beta)) / 2
    return max(0.0, min(poa, 1150.0))


def pv_hours(now: datetime, latitude: float, longitude: float,
             surfaces: list[dict[str, Any]], clouds: dict[datetime, float]) -> dict[datetime, float]:
    """Return hourly PV Wh, only for cloud forecast hours.

    Use two quarter-hour samples per hour for better low-sun estimates.
    Missing cloud hours are omitted, not filled with invented sunshine.
    """
    out = {}
    for hour, cloud in clouds.items():
        if not 0 <= cloud <= 100:
            continue
        # Clear sky scaled to STC rating and system derate, with conservative
        # empirical cloud attenuation. Not site-calibrated.
        factor = max(0.10, 1 - 0.78 * (cloud / 100) ** 1.7)
        value = 0.0
        for surface in surfaces[:4]:
            peak = float(surface.get("kwp", 0))
            if peak <= 0:
                continue
            tilt = float(surface.get("tilt", 0))
            azimuth = float(surface.get("azimuth", 180))
            if not (0 <= tilt <= 90 and 0 <= azimuth <= 360):
                continue
            poa = (_clear_sky_poa(hour + timedelta(minutes=15), latitude, longitude, tilt, azimuth)
                   + _clear_sky_poa(hour + timedelta(minutes=45), latitude, longitude, tilt, azimuth)) / 2
            value += peak * 1000 * (poa / 1000) * 0.85 * factor
        out[hour] = round(value, 2)
    return out
