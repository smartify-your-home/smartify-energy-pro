"""Estimated PV hourly production for up to four separate roof planes.

Uses HA location, STC kWp, tilt (0=flat) and azimuth (0=N, 90=E,
180=S, 270=W). A lightweight clear-sky plane-of-array approximation is
attenuated by the Meteonomiqs hourly cloud cover; bifacial modules add their
rear side (opposite normal) weighted with the bifaciality. This is not a bankable
irradiance simulation and requires measured PV feedback for calibration.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import asin, cos, degrees, exp, isfinite, pi, radians, sin
from typing import Any


def hourly_clouds(attributes: dict, now: datetime, horizon_hours: int = 48) -> dict[datetime, float]:
    """Read UTC hourly cloud slots; default legacy horizon remains 48h."""
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
            if now.astimezone(UTC) - timedelta(hours=1) <= stamp < now.astimezone(UTC) + timedelta(hours=horizon_hours + 1):
                result[stamp] = float(cloud)
        except (ValueError, KeyError, TypeError):
            continue
    return result


def hourly_ghi(attributes: dict, now: datetime) -> dict[datetime, float]:
    """Read GeoSphere C-LAEF hourly GHI in W/m², not a PV energy forecast.

    Only explicitly labelled and time-aligned GeoSphere data are accepted.
    Missing readings are omitted rather than converted to zero or clear sky.
    """
    if (attributes.get("source") != "GeoSphere Austria C-LAEF"
            or attributes.get("dataset") != "nwp-v2-1h-1km"
            or attributes.get("irradiance_unit") != "W/m²"):
        return {}
    rows = attributes.get("forecast")
    if not isinstance(rows, list):
        return {}
    now_utc = now.astimezone(UTC)
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            stamp = datetime.fromisoformat(str(row["datetime"]).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(row["end"]).replace("Z", "+00:00"))
            if stamp.tzinfo is None or end.tzinfo is None:
                continue
            stamp, end = stamp.astimezone(UTC), end.astimezone(UTC)
            if (stamp.minute or stamp.second or stamp.microsecond
                    or end - stamp != timedelta(hours=1)
                    or not now_utc - timedelta(hours=1) <= stamp < now_utc + timedelta(hours=61)):
                continue
            ghi = row.get("ghi_w_m2")
            if (isinstance(ghi, bool) or not isinstance(ghi, (int, float))
                    or not isfinite(ghi) or not 0 <= ghi <= 1800):
                continue
            out[stamp] = float(ghi)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return out


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
            bifaciality = float(surface.get("bifaciality") or 0)
            if 0 < bifaciality <= 1:
                # Rear side of a bifacial module: normal points the opposite way
                # (tilt 180°−tilt, azimuth +180°) – direct sun from behind, sky
                # diffuse and ground reflection – weighted with the bifaciality.
                rear_tilt, rear_az = 180 - tilt, (azimuth + 180) % 360
                rear = (_clear_sky_poa(hour + timedelta(minutes=15), latitude, longitude, rear_tilt, rear_az)
                        + _clear_sky_poa(hour + timedelta(minutes=45), latitude, longitude, rear_tilt, rear_az)) / 2
                poa += bifaciality * rear
            value += peak * 1000 * (poa / 1000) * 0.85 * factor
        out[hour] = round(value, 2)
    return out


def pv_hours_ghi(now: datetime, latitude: float, longitude: float,
                 surfaces: list[dict[str, Any]], ghi_hours: dict[datetime, float]) -> dict[datetime, float]:
    """Convert GeoSphere horizontal GHI into estimated per-surface AC Wh.

    Apply the forecast/clear-sky horizontal irradiation ratio to the existing
    clear-sky plane-of-array estimate for each roof surface, including bifacial
    rear contribution. This is an approximate irradiance transposition (not a
    measured direct/diffuse split). Do NOT additionally attenuate by cloud%.
    """
    result = {}
    for hour, ghi in ghi_hours.items():
        if (not isinstance(ghi, (float, int)) or isinstance(ghi, bool)
                or not isfinite(ghi) or not 0 <= ghi <= 1800):
            continue
        t1, t2 = hour + timedelta(minutes=15), hour + timedelta(minutes=45)
        clear_ghi = (_clear_sky_poa(t1, latitude, longitude, 0, 180)
                     + _clear_sky_poa(t2, latitude, longitude, 0, 180)) / 2
        # No division by nearly-zero solar altitude near dawn/dusk. A physical
        # 0 W/m² forecast remains a valid zero-production hour.
        ratio = min(1.3, ghi / clear_ghi) if clear_ghi >= 10 else 0.0
        value = 0.0
        for surface in surfaces[:4]:
            peak = float(surface.get("kwp") or 0)
            if peak <= 0:
                continue
            tilt = float(surface.get("tilt", 0))
            azimuth = float(surface.get("azimuth", 180))
            if not (0 <= tilt <= 90 and 0 <= azimuth <= 360):
                continue
            poa = (_clear_sky_poa(t1, latitude, longitude, tilt, azimuth)
                   + _clear_sky_poa(t2, latitude, longitude, tilt, azimuth)) / 2
            bifaciality = float(surface.get("bifaciality") or 0)
            if 0 < bifaciality <= 1:
                rear_tilt, rear_az = 180 - tilt, (azimuth + 180) % 360
                poa += bifaciality * (
                    _clear_sky_poa(t1, latitude, longitude, rear_tilt, rear_az)
                    + _clear_sky_poa(t2, latitude, longitude, rear_tilt, rear_az)
                ) / 2
            value += peak * 1000 * (poa / 1000) * 0.85 * ratio
        result[hour] = round(value, 2)
    return result
