"""Water balance calculations for irrigation control (NFK bilanz)."""

from dataclasses import dataclass
from datetime import date


@dataclass
class DailyBalance:
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
    """NFK balance: nfk_ende = nfk_anfang - etc + regen + beregnung, clamped [0, nfk_max]."""
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
    """ETc = ET₀ × Kc × Ka, floored at 0."""
    return max(0.0, et0 * kc * ka)


def needs_watering(nfk_aktuell: float, nfk_max: float, schwellwert_pct: float) -> bool:
    """True if nfk_aktuell < nfk_max × schwellwert_pct / 100."""
    threshold = nfk_max * schwellwert_pct / 100.0
    return nfk_aktuell < threshold


def watering_dauer_min(
    nfk_aktuell: float,
    nfk_max: float,
    zielwert_pct: float,
    durchfluss_mm_min: float,
) -> float:
    """Minutes to irrigate from current NFK to target; 0.0 if already there or no flow."""
    if durchfluss_mm_min <= 0:
        return 0.0

    target = nfk_max * zielwert_pct / 100.0
    if nfk_aktuell >= target:
        return 0.0

    return (target - nfk_aktuell) / durchfluss_mm_min
