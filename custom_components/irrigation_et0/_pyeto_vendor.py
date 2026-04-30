"""
Vendored subset of PyETo for FAO-56 ET0 calculations.

Source: https://github.com/woodcrafty/PyETo
License: BSD 3-Clause (original), vendored under same terms.
Vendored commit: d5f1809 (2018-07-31)
Only pure math functions included. No modification to algorithms.
"""
import math

# Solar constant [MJ m-2 min-1]
_GSC = 0.0820

# Stefan-Boltzmann constant [MJ K-4 m-2 day-1]
_SIGMA = 4.903e-9


def atmos_pres(altitude: float) -> float:
    """Estimate atmospheric pressure from altitude.

    Based on FAO-56 equation 7.

    :param altitude: Elevation above sea level [m]
    :return: Atmospheric pressure [kPa]
    """
    return 101.3 * ((293.0 - 0.0065 * altitude) / 293.0) ** 5.26


def psy_const(atmos_pres: float) -> float:
    """Calculate the psychrometric constant.

    Based on FAO-56 equation 8.

    :param atmos_pres: Atmospheric pressure [kPa]
    :return: Psychrometric constant [kPa degC-1]
    """
    return 0.000665 * atmos_pres


def svp_from_t(t: float) -> float:
    """Estimate saturation vapour pressure from temperature.

    Based on FAO-56 equation 11.

    :param t: Temperature [degC]
    :return: Saturation vapour pressure [kPa]
    """
    return 0.6108 * math.exp((17.27 * t) / (t + 237.3))


def mean_svp(svp_tmin: float, svp_tmax: float) -> float:
    """Estimate mean saturation vapour pressure.

    Based on FAO-56 equation 12.

    :param svp_tmin: Saturation vapour pressure at daily minimum temperature [kPa]
    :param svp_tmax: Saturation vapour pressure at daily maximum temperature [kPa]
    :return: Mean saturation vapour pressure [kPa]
    """
    return (svp_tmax + svp_tmin) / 2.0


def avp_from_rhmin_rhmax(svp_tmin: float, svp_tmax: float, rhmin: float, rhmax: float) -> float:
    """Estimate actual vapour pressure from minimum and maximum relative humidity.

    Based on FAO-56 equation 17.

    :param svp_tmin: Saturation vapour pressure at daily minimum temperature [kPa]
    :param svp_tmax: Saturation vapour pressure at daily maximum temperature [kPa]
    :param rhmin: Minimum relative humidity [%]
    :param rhmax: Maximum relative humidity [%]
    :return: Actual vapour pressure [kPa]
    """
    return (svp_tmin * (rhmax / 100.0) + svp_tmax * (rhmin / 100.0)) / 2.0


def delta_svp(t: float) -> float:
    """Calculate the slope of the saturation vapour pressure curve.

    Based on FAO-56 equation 13.

    :param t: Temperature [degC]
    :return: Slope of saturation vapour pressure curve [kPa degC-1]
    """
    tmp = 0.6108 * math.exp(17.27 * t / (t + 237.3))
    return 4098.0 * tmp / (t + 237.3) ** 2


def sol_dec(day_of_year: int) -> float:
    """Calculate solar declination.

    Based on FAO-56 equation 24.

    :param day_of_year: Day of year (1-366)
    :return: Solar declination [radians]
    """
    return 0.409 * math.sin(((2.0 * math.pi / 365.0) * day_of_year) - 1.39)


def inv_rel_dist_earth_sun(day_of_year: int) -> float:
    """Calculate the inverse relative distance between earth and sun.

    Based on FAO-56 equation 23.

    :param day_of_year: Day of year (1-366)
    :return: Inverse relative distance between earth and sun [dimensionless]
    """
    return 1 + (0.033 * math.cos((2.0 * math.pi / 365.0) * day_of_year))


def sunset_hour_angle(latitude: float, sol_dec: float) -> float:
    """Calculate sunset hour angle.

    Based on FAO-56 equation 25.

    :param latitude: Latitude [radians]
    :param sol_dec: Solar declination [radians]
    :return: Sunset hour angle [radians]
    """
    cos_sha = -math.tan(latitude) * math.tan(sol_dec)
    # Clamp to [-1, 1] to avoid domain errors at extreme latitudes
    cos_sha = max(-1.0, min(1.0, cos_sha))
    return math.acos(cos_sha)


def et_rad(latitude: float, sol_dec: float, sha: float, ird: float) -> float:
    """Estimate daily extraterrestrial radiation (Ra).

    Based on FAO-56 equation 21.

    :param latitude: Latitude [radians]
    :param sol_dec: Solar declination [radians]
    :param sha: Sunset hour angle [radians]
    :param ird: Inverse relative distance earth-sun [dimensionless]
    :return: Daily extraterrestrial radiation [MJ m-2 day-1]
    """
    tmp1 = (24.0 * 60.0) / math.pi
    tmp2 = sha * math.sin(latitude) * math.sin(sol_dec)
    tmp3 = math.cos(latitude) * math.cos(sol_dec) * math.sin(sha)
    return tmp1 * _GSC * ird * (tmp2 + tmp3)


def cs_rad(altitude: float, et_rad: float) -> float:
    """Estimate clear sky radiation (Rso).

    Based on FAO-56 equation 37.

    :param altitude: Elevation above sea level [m]
    :param et_rad: Extraterrestrial radiation [MJ m-2 day-1]
    :return: Clear sky radiation [MJ m-2 day-1]
    """
    return (0.75 + (2e-5 * altitude)) * et_rad


def net_in_sol_rad(sol_rad: float, albedo: float = 0.23) -> float:
    """Calculate net incoming solar (shortwave) radiation.

    Based on FAO-56 equation 38.

    :param sol_rad: Gross incoming solar radiation [MJ m-2 day-1]
    :param albedo: Albedo of the crop as the fraction of incident radiation
        reflected by the surface. Default is 0.23 for the grass reference crop.
    :return: Net incoming solar (shortwave) radiation [MJ m-2 day-1]
    """
    return (1.0 - albedo) * sol_rad


def net_out_lw_rad(tmin: float, tmax: float, sol_rad: float, cs_rad: float, avp: float) -> float:
    """Estimate net outgoing longwave radiation.

    Based on FAO-56 equation 39.

    :param tmin: Minimum daily temperature [degC]
    :param tmax: Maximum daily temperature [degC]
    :param sol_rad: Solar radiation [MJ m-2 day-1]
    :param cs_rad: Clear sky radiation [MJ m-2 day-1]
    :return: Net outgoing longwave radiation [MJ m-2 day-1]
    """
    tmin_k = tmin + 273.16
    tmax_k = tmax + 273.16
    tmp1 = _SIGMA * ((tmax_k ** 4 + tmin_k ** 4) / 2.0)
    tmp2 = 0.34 - (0.14 * math.sqrt(avp))
    tmp3 = (1.35 * (sol_rad / cs_rad)) - 0.35
    return tmp1 * tmp2 * tmp3


def fao56_penman_monteith(
    net_rad: float,
    t: float,
    ws: float,
    svp: float,
    avp: float,
    delta_svp: float,
    psy: float,
    shf: float = 0.0,
) -> float:
    """Estimate reference evapotranspiration (ET0) using the FAO-56 Penman-Monteith equation.

    Based on FAO-56 equation 6.

    :param net_rad: Net radiation at the crop surface [MJ m-2 day-1]
    :param t: Air temperature at 2m height [degC]
    :param ws: Wind speed at 2m height [m s-1]
    :param svp: Saturation vapour pressure [kPa]
    :param avp: Actual vapour pressure [kPa]
    :param delta_svp: Slope of saturation vapour pressure curve [kPa degC-1]
    :param psy: Psychrometric constant [kPa degC-1]
    :param shf: Soil heat flux density [MJ m-2 day-1]. Usually small compared
        to net_rad and can be omitted. Default is 0.
    :return: Reference evapotranspiration ET0 [mm day-1]
    """
    a1 = 0.408 * (net_rad - shf) * delta_svp
    a2 = psy * (900.0 / (t + 273.0)) * ws * (svp - avp)
    b1 = delta_svp + psy * (1.0 + 0.34 * ws)
    return (a1 + a2) / b1


def hargreaves(tmin: float, tmax: float, et_rad: float) -> float:
    """Estimate reference evapotranspiration using the Hargreaves equation.

    Based on the Hargreaves (1994) equation.

    :param tmin: Minimum daily temperature [degC]
    :param tmax: Maximum daily temperature [degC]
    :param et_rad: Extraterrestrial radiation [MJ m-2 day-1]
    :return: Reference evapotranspiration ET0 [mm day-1]
    """
    return 0.0023 * (((tmin + tmax) / 2.0) + 17.8) * (tmax - tmin) ** 0.5 * et_rad
