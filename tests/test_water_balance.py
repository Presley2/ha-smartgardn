"""Tests for the water_balance module."""
from datetime import date

import pytest

from custom_components.smartgardn_et0.water_balance import (
    calc_daily_balance,
    calc_etc,
    needs_watering,
    watering_dauer_min,
)


def test_calc_daily_balance_clamps_zero():
    result = calc_daily_balance(
        datum=date(2025, 6, 1),
        nfk_anfang=2.0,
        etc=10.0,
        regen=0.0,
        beregnung=0.0,
        nfk_max=15.0,
    )
    assert result.nfk_ende == 0.0


def test_calc_daily_balance_clamps_max_on_overflow():
    result = calc_daily_balance(
        datum=date(2025, 6, 1),
        nfk_anfang=14.0,
        etc=0.0,
        regen=5.0,
        beregnung=5.0,
        nfk_max=15.0,
    )
    assert result.nfk_ende == 15.0


def test_calc_daily_balance_normal_case():
    result = calc_daily_balance(
        datum=date(2025, 6, 1),
        nfk_anfang=10.0,
        etc=2.0,
        regen=1.0,
        beregnung=0.0,
        nfk_max=15.0,
    )
    assert result.nfk_ende == 9.0


def test_calc_daily_balance_datum_preserved():
    test_date = date(2025, 7, 15)
    result = calc_daily_balance(
        datum=test_date,
        nfk_anfang=10.0,
        etc=2.0,
        regen=1.0,
        beregnung=0.0,
        nfk_max=15.0,
    )
    assert result.datum == test_date


def test_calc_etc_multiplies_factors():
    result = calc_etc(et0=4.0, kc=0.8, ka=1.0)
    assert result == 3.2


def test_calc_etc_floored_at_zero():
    result = calc_etc(et0=-2.0, kc=0.5, ka=1.0)
    assert result == 0.0


def test_needs_watering_below_threshold():
    result = needs_watering(nfk_aktuell=4.0, nfk_max=15.0, schwellwert_pct=50)
    assert result is True


def test_needs_watering_at_threshold():
    result = needs_watering(nfk_aktuell=7.5, nfk_max=15.0, schwellwert_pct=50)
    assert result is False


def test_dauer_returns_zero_when_above_zielwert():
    result = watering_dauer_min(
        nfk_aktuell=12.0,
        nfk_max=15.0,
        zielwert_pct=80,
        durchfluss_mm_min=0.8,
    )
    assert result == 0.0


def test_dauer_for_typical_zone():
    result = watering_dauer_min(
        nfk_aktuell=5.0,
        nfk_max=15.0,
        zielwert_pct=80,
        durchfluss_mm_min=0.8,
    )
    assert result == 8.75


def test_calc_etc_with_seasonal_factor():
    # ka < 1 reduces ETc proportionally
    assert calc_etc(et0=4.0, kc=0.8, ka=0.7) == pytest.approx(2.24)


def test_dauer_zero_when_no_flow():
    assert watering_dauer_min(5.0, 15.0, 80, 0.0) == 0.0
