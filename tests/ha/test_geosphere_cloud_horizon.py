"""End-to-end forecast provider tests for GeoSphere cloud cover (no live API)."""
from datetime import timedelta

from homeassistant.util import dt as dt_util

from custom_components.smartify_energy.forecast import ForecastProvider

PV_SURFACES = [{"kwp": 10, "tilt": 20, "azimuth": 180}]


def _cloud_attrs(start, count=60, *, source="GeoSphere Austria C-LAEF",
                 dataset="nwp-v2-1h-1km", max_hours=60):
    rows = [
        {
            "datetime": (start + timedelta(hours=i)).isoformat(),
            "end": (start + timedelta(hours=i + 1)).isoformat(),
            "cloud_coverage": 10 if i % 2 == 0 else 85,
            "ghi_w_m2": None,  # Cloud model must not require GHI.
        }
        for i in range(count)
    ]
    return {
        "source": source, "dataset": dataset, "max_forecast_hours": max_hours,
        "forecast": rows, "irradiance_unit": "W/m²",
    }


async def _forecast(hass, attrs):
    hass.config.latitude, hass.config.longitude = 48.0, 13.0
    entity = "sensor.weather_test_cloud"
    hass.states.async_set(entity, "43", attrs)
    fc = ForecastProvider(hass, [], [], solar_config={
        "mode": "calculated", "weather_source": "cloud",
        "cloud_entity": entity, "surfaces": PV_SURFACES,
        "calibration_enabled": False,
    })
    await fc.async_refresh()
    assert fc.error is None
    return fc


async def test_geosphere_cloud_60h_used_by_real_forecast_provider(hass):
    start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    fc = await _forecast(hass, _cloud_attrs(start))
    assert len(fc.hours) == 60
    assert len(fc.raw_hours) == 60
    assert len(fc.cloud_hours) == 60
    assert fc.source_label == "GeoSphere Austria C-LAEF (Bewölkung)"
    last_hour = dt_util.as_local(start + timedelta(hours=59))
    assert last_hour in fc.hours
    assert fc.hours[last_hour] >= 0
    assert fc.base_hours == fc.hours


async def test_meteonomiqs_stays_on_legacy_horizon(hass):
    start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    fc = await _forecast(hass, _cloud_attrs(start, source="Meteonomiqs"))
    # The legacy time window includes the current partial hour and its
    # forward boundary: 49 or 50 slots depending on the clock minute.
    assert 49 <= len(fc.hours) <= 50
    assert dt_util.as_local(start + timedelta(hours=50)) not in fc.hours
    assert fc.source_label == "Eigene Berechnung"


async def test_short_and_missing_geosphere_cloud_slots_not_filled(hass):
    start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    attrs = _cloud_attrs(start, count=16)
    attrs["forecast"].pop(10)
    fc = await _forecast(hass, attrs)
    assert len(fc.hours) == 15
    gap = dt_util.as_local(start + timedelta(hours=10))
    assert gap not in fc.hours
    final = dt_util.as_local(start + timedelta(hours=15))
    assert final in fc.hours
