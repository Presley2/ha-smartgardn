"""Tests for the et0_calculator module."""
import pytest
from custom_components.irrigation_et0.et0_calculator import (
    calc_et0_fao56,
    calc_et0_hargreaves,
    calc_et0_haude,
    calc_ka,
    Et0Result,
)


def test_calc_et0_fao56_returns_positive_for_summer_input():
    # lat=50°N, DOY=180 (summer solstice), reasonable summer values
    et0 = calc_et0_fao56(12.0, 28.0, 40.0, 80.0, 200.0, 2.0, 50.0, 163, 180)
    assert et0 > 0


def test_calc_et0_fao56_clamps_unrealistic_inputs():
    # solar=2000 W/m² (above limit of 1500) → should still return valid float
    et0 = calc_et0_fao56(12.0, 28.0, 40.0, 80.0, 2000.0, 2.0, 50.0, 163, 180)
    assert isinstance(et0, float) and et0 > 0


def test_calc_et0_fao56_with_swapped_temps_normalizes():
    # t_min > t_max → swap internally, don't crash
    et0 = calc_et0_fao56(28.0, 12.0, 40.0, 80.0, 200.0, 2.0, 50.0, 163, 180)
    assert et0 > 0


def test_calc_et0_hargreaves_known_value():
    # lat=50°N, DOY=180: Ra ≈ 41 MJ/m²/d → Hargreaves gives ~14.5 mm/day
    et0 = calc_et0_hargreaves(12.0, 28.0, 50.0, 180)
    assert 2.0 < et0 < 20.0


def test_calc_et0_haude_monthly_factor():
    # May (month=5) has fH=0.41, higher than Jan (0.22)
    et0_may = calc_et0_haude(22.0, 50.0, 5)
    et0_jan = calc_et0_haude(22.0, 50.0, 1)
    assert et0_may > et0_jan


def test_negative_solar_treated_as_zero():
    # Negative solar should be clamped to 0, not crash
    et0_neg = calc_et0_fao56(12.0, 28.0, 40.0, 80.0, -100.0, 2.0, 50.0, 163, 180)
    et0_zero = calc_et0_fao56(12.0, 28.0, 40.0, 80.0, 0.0, 2.0, 50.0, 163, 180)
    assert abs(et0_neg - et0_zero) < 0.01


def test_calc_ka_at_known_temps():
    ka_low = calc_ka(10.0)   # 0.6 + 0.28 - 0.02 = 0.86
    ka_high = calc_ka(30.0)  # 0.6 + 0.84 - 0.18 = 1.26
    assert abs(ka_low - 0.86) < 0.01
    assert abs(ka_high - 1.26) < 0.01


def test_calc_ka_clamped_to_bounds():
    assert calc_ka(-50.0) == 0.4   # below min → clamped to 0.4
    assert calc_ka(100.0) == 1.4   # would exceed max → clamped to 1.4
