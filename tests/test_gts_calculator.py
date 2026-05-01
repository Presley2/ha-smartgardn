"""Tests for the gts_calculator module."""
from datetime import date

from custom_components.smartgardn_et0.gts_calculator import (
    gts_increment,
    gts_should_reset,
    gts_weight,
)


def test_gts_weight_january():
    assert gts_weight(1) == 0.5


def test_gts_weight_february():
    assert gts_weight(2) == 0.75


def test_gts_weight_march():
    assert gts_weight(3) == 1.0


def test_gts_weight_april():
    assert gts_weight(4) == 1.0


def test_gts_weight_may():
    assert gts_weight(5) == 1.0


def test_gts_weight_june():
    assert gts_weight(6) == 1.0


def test_gts_weight_july():
    assert gts_weight(7) == 1.0


def test_gts_weight_august():
    assert gts_weight(8) == 1.0


def test_gts_weight_september():
    assert gts_weight(9) == 1.0


def test_gts_weight_october():
    assert gts_weight(10) == 1.0


def test_gts_weight_november():
    assert gts_weight(11) == 1.0


def test_gts_weight_december():
    assert gts_weight(12) == 1.0


def test_gts_increment_positive_temp():
    assert gts_increment(10.0, 3) == 10.0


def test_gts_increment_january_weight():
    assert gts_increment(8.0, 1) == 4.0


def test_gts_increment_negative_temp_ignored():
    assert gts_increment(-3.0, 5) == 0.0


def test_gts_increment_zero_temp():
    assert gts_increment(0.0, 6) == 0.0


def test_gts_should_reset_on_jan1_with_no_prior_reset():
    assert gts_should_reset(date(2025, 1, 1), None) is True


def test_gts_should_reset_on_jan1_with_prior_year_reset():
    assert gts_should_reset(date(2025, 1, 1), date(2024, 1, 1)) is True


def test_gts_should_not_reset_on_jan1_if_already_reset_today():
    assert gts_should_reset(date(2025, 1, 1), date(2025, 1, 1)) is False


def test_gts_should_not_reset_on_other_days():
    assert gts_should_reset(date(2025, 6, 15), date(2025, 1, 1)) is False
