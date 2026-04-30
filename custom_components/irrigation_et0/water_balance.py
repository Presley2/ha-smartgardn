"""Water balance calculations for irrigation control (NFK bilanz)."""
from dataclasses import dataclass
from datetime import date


@dataclass
class DailyBalance:
    """Daily water balance for a soil zone."""

    datum: date
    nfk_anfang: float
    etc: float
    regen: float
    beregnung: float
    nfk_ende: float


def calc_daily_balance(
    datum: date,
    nfk_anfang: float,
    etc: float,
    regen: float,
    beregnung: float,
    nfk_max: float,
) -> DailyBalance:
    """Calculate daily water balance.

    NFK balance: nfk_ende = nfk_anfang - etc + regen + beregnung,
    clamped to [0, nfk_max].

    Args:
        datum: Date of the balance.
        nfk_anfang: Soil water at start of day [mm].
        etc: Crop evapotranspiration [mm].
        regen: Rainfall [mm].
        beregnung: Irrigation applied [mm].
        nfk_max: Maximum available water capacity [mm].

    Returns:
        DailyBalance with nfk_ende clamped to [0, nfk_max].
    """
    nfk_raw = nfk_anfang - etc + regen + beregnung
    nfk_ende = max(0.0, min(nfk_raw, nfk_max))

    return DailyBalance(
        datum=datum,
        nfk_anfang=nfk_anfang,
        etc=etc,
        regen=regen,
        beregnung=beregnung,
        nfk_ende=nfk_ende,
    )


def calc_etc(et0: float, kc: float, ka: float) -> float:
    """Calculate crop evapotranspiration.

    ETc = ET₀ × Kc × Ka, floored at 0.

    Args:
        et0: Reference evapotranspiration [mm].
        kc: Crop coefficient.
        ka: Temperature adjustment factor.

    Returns:
        ETc [mm], at least 0.0.
    """
    return max(0.0, et0 * kc * ka)


def needs_watering(nfk_aktuell: float, nfk_max: float, schwellwert_pct: float) -> bool:
    """Check if watering is needed.

    Returns True if nfk_aktuell < nfk_max * schwellwert_pct / 100.

    Args:
        nfk_aktuell: Current soil water [mm].
        nfk_max: Maximum available water capacity [mm].
        schwellwert_pct: Watering threshold as percentage of nfk_max.

    Returns:
        True if current water is below threshold.
    """
    threshold = nfk_max * schwellwert_pct / 100.0
    return nfk_aktuell < threshold


def watering_dauer_min(
    nfk_aktuell: float,
    nfk_max: float,
    zielwert_pct: float,
    durchfluss_mm_min: float,
) -> float:
    """Calculate irrigation duration in minutes.

    Minutes to water from nfk_aktuell up to nfk_max * zielwert_pct / 100.

    Args:
        nfk_aktuell: Current soil water [mm].
        nfk_max: Maximum available water capacity [mm].
        zielwert_pct: Target water level as percentage of nfk_max.
        durchfluss_mm_min: Irrigation rate [mm/min].

    Returns:
        Minutes needed to reach target, or 0.0 if already at/above target
        or durchfluss_mm_min <= 0.
    """
    if durchfluss_mm_min <= 0:
        return 0.0

    target = nfk_max * zielwert_pct / 100.0
    if nfk_aktuell >= target:
        return 0.0

    return (target - nfk_aktuell) / durchfluss_mm_min
