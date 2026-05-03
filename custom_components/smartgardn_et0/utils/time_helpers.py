"""Time and scheduling helper functions."""

from __future__ import annotations

from datetime import date, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def get_next_enabled_weekday(
    weekdays_enabled: dict[str, bool],
    start_date: date | None = None,
) -> date | None:
    """Find next enabled weekday.

    Args:
        weekdays_enabled: Dict with weekday names as keys, bool as values
        start_date: Starting date (default: tomorrow)

    Returns:
        Next enabled weekday or None if none found in next 7 days
    """
    if start_date is None:
        start_date = date.today()

    for i in range(1, 8):
        check_date = start_date + timedelta(days=i)
        weekday_name = WEEKDAYS[check_date.weekday()]
        if weekdays_enabled.get(weekday_name, True):
            return check_date
    return None


def check_rain_skip(
    forecast: list,
    target_date_offset: int,
    threshold_mm: float,
) -> bool:
    """Check if rain forecast exceeds threshold for a day.

    Args:
        forecast: List of forecast objects with precip_sum attribute
        target_date_offset: 1=tomorrow, 2=day-after-tomorrow
        threshold_mm: Rain threshold in mm

    Returns:
        True if rain >= threshold, False otherwise
    """
    idx = target_date_offset - 1
    if idx < len(forecast):
        return forecast[idx].precip_sum >= threshold_mm
    return False
