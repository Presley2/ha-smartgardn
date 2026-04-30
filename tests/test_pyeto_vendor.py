"""Tests for vendored PyETo functions."""
import json
import math
from pathlib import Path
import pytest
from custom_components.irrigation_et0._pyeto_vendor import (
    fao56_penman_monteith, hargreaves, delta_svp, psy_const,
    svp_from_t, avp_from_rhmin_rhmax, mean_svp, atmos_pres,
    sol_dec, inv_rel_dist_earth_sun, sunset_hour_angle,
    et_rad, cs_rad, net_in_sol_rad, net_out_lw_rad,
)

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "fao_annex6_examples.json").read_text())

def test_fao_annex6_example():
    """Reproduce FAO-56 Chapter 4 worked example within 0.15 mm tolerance."""
    inp = FIXTURES["chapter4_example"]["inputs"]
    expected = FIXTURES["chapter4_example"]["expected_et0_mm"]

    lat = math.radians(inp["latitude_deg"])
    doy = inp["day_of_year"]
    alt = inp["altitude"]

    # Compute intermediate values
    sd = sol_dec(doy)
    ird = inv_rel_dist_earth_sun(doy)
    sha = sunset_hour_angle(lat, sd)
    ra = et_rad(lat, sd, sha, ird)
    rso = cs_rad(alt, ra)
    p = atmos_pres(alt)

    svp_min = svp_from_t(inp["t_min"])
    svp_max = svp_from_t(inp["t_max"])
    es = mean_svp(svp_min, svp_max)
    ea = avp_from_rhmin_rhmax(svp_min, svp_max, inp["rh_min"], inp["rh_max"])

    rns = net_in_sol_rad(inp["solar_rad_mj"])
    rnl = net_out_lw_rad(inp["t_min"], inp["t_max"], inp["solar_rad_mj"], rso, ea)
    rn = rns - rnl

    dsvp = delta_svp((inp["t_min"] + inp["t_max"]) / 2)
    psy = psy_const(p)

    t_mean = (inp["t_min"] + inp["t_max"]) / 2
    et0 = fao56_penman_monteith(rn, t_mean, inp["u2"], es, ea, dsvp, psy)

    assert abs(et0 - expected) < 0.15, f"ET0={et0:.2f}, expected~{expected}"

def test_hargreaves_known_value():
    """Test Hargreaves formula produces reasonable value for a mild winter day at 45N.

    DOY=30 (Jan 30) at lat=45N gives Ra~14 MJ m-2 d-1; with tmin=5, tmax=20
    the Hargreaves equation yields ET0 in the 3-6 mm/day range.
    """
    lat = math.radians(45.0)
    doy = 30  # late January, low Ra (~14 MJ m-2 d-1)
    sd = sol_dec(doy)
    ird = inv_rel_dist_earth_sun(doy)
    sha = sunset_hour_angle(lat, sd)
    ra = et_rad(lat, sd, sha, ird)

    et0 = hargreaves(5.0, 20.0, ra)
    assert 3.0 < et0 < 7.0, f"Hargreaves ET0={et0:.2f} outside expected range"

def test_psychrometric_constant_at_sea_level():
    """gamma at sea level (P~101.3 kPa) should be ~0.0674."""
    p = atmos_pres(0)
    psy = psy_const(p)
    assert abs(psy - 0.0674) < 0.002

def test_svp_at_20c():
    """Saturation vapour pressure at 20 degrees C should be ~2.338 kPa."""
    svp = svp_from_t(20.0)
    assert abs(svp - 2.338) < 0.01

def test_delta_svp_positive():
    """Slope of SVP curve should always be positive."""
    for t in range(-10, 50):
        assert delta_svp(float(t)) > 0
