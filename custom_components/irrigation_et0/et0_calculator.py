"""ET₀ calculator module — FAO-56 PM, Hargreaves, Haude, Ka."""

import math
from dataclasses import dataclass

from custom_components.irrigation_et0._pyeto_vendor import (
    atmos_pres,
    avp_from_rhmin_rhmax,
    cs_rad,
    delta_svp,
    et_rad,
    fao56_penman_monteith,
    hargreaves,
    inv_rel_dist_earth_sun,
    mean_svp,
    net_in_sol_rad,
    net_out_lw_rad,
    psy_const,
    sol_dec,
    sunset_hour_angle,
    svp_from_t,
)
from custom_components.irrigation_et0.const import SENSOR_LIMITS

# Unit conversion: W/m² × 0.0864 = MJ/m²/day
W_M2_TO_MJ_M2_D = 0.0864

# Haude monthly factors (Jan=1 … Dec=12)
_HAUDE_MONTHLY_FACTORS = {
    1: 0.22,
    2: 0.22,
    3: 0.27,
    4: 0.35,
    5: 0.41,
    6: 0.41,
    7: 0.38,
    8: 0.38,
    9: 0.32,
    10: 0.27,
    11: 0.22,
    12: 0.22,
}


def _clamp(value: float, key: str) -> float:
    lo, hi = SENSOR_LIMITS[key]
    return max(lo, min(hi, value))


def calc_et0_fao56(
    t_min: float,  # °C
    t_max: float,  # °C
    rh_min: float,  # %
    rh_max: float,  # %
    solar_w_m2: float,  # W/m² (measured; convert internally to MJ/m²/d)
    wind_m_s: float,  # m/s at 2m height
    latitude: float,  # decimal degrees (NOT radians)
    elevation: float,  # metres
    day_of_year: int,  # 1–365
) -> float:
    """Return daily FAO-56 Penman-Monteith ET₀ in mm/day."""
    # Clamp inputs
    t_min = _clamp(t_min, "temp")
    t_max = _clamp(t_max, "temp")
    rh_min = _clamp(rh_min, "humidity")
    rh_max = _clamp(rh_max, "humidity")
    solar_w_m2 = _clamp(solar_w_m2, "solar")
    wind_m_s = _clamp(wind_m_s, "wind")

    # Normalise temperature ordering
    if t_min > t_max:
        t_min, t_max = t_max, t_min

    # Normalise humidity ordering
    if rh_min > rh_max:
        rh_min, rh_max = rh_max, rh_min

    # Convert solar radiation to MJ/m²/day
    sol_rad_mj = solar_w_m2 * W_M2_TO_MJ_M2_D

    # Convert latitude to radians
    lat_rad = math.radians(latitude)

    # Mean daily temperature
    t_mean = (t_min + t_max) / 2.0

    # Vapour pressure terms
    svp_tmin = svp_from_t(t_min)
    svp_tmax = svp_from_t(t_max)
    svp = mean_svp(svp_tmin, svp_tmax)
    avp = avp_from_rhmin_rhmax(svp_tmin, svp_tmax, rh_min, rh_max)

    # Slope of SVP curve at mean temperature
    d_svp = delta_svp(t_mean)

    # Atmospheric pressure and psychrometric constant
    atm_p = atmos_pres(elevation)
    psy = psy_const(atm_p)

    # Extraterrestrial radiation
    sd = sol_dec(day_of_year)
    ird = inv_rel_dist_earth_sun(day_of_year)
    sha = sunset_hour_angle(lat_rad, sd)
    ra = et_rad(lat_rad, sd, sha, ird)

    # Clear-sky radiation
    rso = cs_rad(elevation, ra)

    # Net shortwave radiation
    rns = net_in_sol_rad(sol_rad_mj)

    # Net longwave radiation — guard against division by zero when rso=0
    if rso > 0:  # noqa: SIM108
        rnl = net_out_lw_rad(t_min, t_max, sol_rad_mj, rso, avp)
    else:
        rnl = 0.0

    # Net radiation
    rn = rns - rnl

    # FAO-56 PM
    et0 = fao56_penman_monteith(rn, t_mean, wind_m_s, svp, avp, d_svp, psy)
    return float(max(0.0, et0))


def calc_et0_hargreaves(
    t_min: float,  # °C
    t_max: float,  # °C
    latitude: float,  # decimal degrees
    day_of_year: int,  # 1–365
) -> float:
    """Return daily Hargreaves ET₀ in mm/day."""
    # Clamp inputs
    t_min = _clamp(t_min, "temp")
    t_max = _clamp(t_max, "temp")

    # Normalise temperature ordering
    if t_min > t_max:
        t_min, t_max = t_max, t_min

    lat_rad = math.radians(latitude)

    sd = sol_dec(day_of_year)
    ird = inv_rel_dist_earth_sun(day_of_year)
    sha = sunset_hour_angle(lat_rad, sd)
    ra = et_rad(lat_rad, sd, sha, ird)

    et0 = hargreaves(t_min, t_max, ra)
    return float(et0)


def calc_et0_haude(
    t14: float,  # temperature at 14:00 (°C)
    rh14: float,  # relative humidity at 14:00 (%)
    month: int,  # 1–12
) -> float:
    """Return daily Haude ET₀ in mm/day.

    Uses Haude monthly factors (fH):
    Jan 0.22, Feb 0.22, Mar 0.27, Apr 0.35, May 0.41, Jun 0.41,
    Jul 0.38, Aug 0.38, Sep 0.32, Oct 0.27, Nov 0.22, Dec 0.22
    Formula: ET₀ = fH × E₀; E₀ = 0.6107 × 10^(7.45×T14/(235+T14)) × (1 - rh14/100)
    """
    if month not in _HAUDE_MONTHLY_FACTORS:
        raise ValueError(f"month must be 1–12, got {month!r}")
    t14 = _clamp(t14, "temp")
    rh14 = _clamp(rh14, "humidity")

    fh = _HAUDE_MONTHLY_FACTORS[month]
    e0 = 0.6107 * math.pow(10.0, 7.45 * t14 / (235.0 + t14)) * (1.0 - rh14 / 100.0)
    return float(fh * e0)


def calc_ka(t_max: float) -> float:
    """Geisenheimer seasonal climate correction factor.

    Ka = 0.6 + 0.028 × T_max - 0.0002 × T_max²
    Clamped to [0.4, 1.4].
    """
    ka = 0.6 + 0.028 * t_max - 0.0002 * t_max**2
    return float(max(0.4, min(1.4, ka)))


@dataclass
class Et0Result:
    """Structured ET₀ result with value, method, and fallback reason."""

    et0_mm: float
    method_used: str  # "fao56", "hargreaves", "haude", "last_known", "zero"
    fallback_reason: str | None  # None if primary method succeeded
