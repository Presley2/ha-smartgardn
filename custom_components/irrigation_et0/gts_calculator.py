"""GTS calculator module — Grünlandtemperatursumme (cumulative growing-degree sum)."""
from datetime import date


def gts_weight(month: int) -> float:
    """Weight factor: 0.5 for Jan, 0.75 for Feb, 1.0 otherwise."""
    if month == 1:
        return 0.5
    elif month == 2:
        return 0.75
    else:
        return 1.0


def gts_increment(t_mittel: float, month: int) -> float:
    """Daily GTS increment = max(0, t_mittel) * gts_weight(month)."""
    return max(0.0, t_mittel) * gts_weight(month)


def gts_should_reset(today: date, last_reset: date | None) -> bool:
    """True if today is Jan 1 and last_reset is not already today."""
    is_jan1 = today.month == 1 and today.day == 1
    if not is_jan1:
        return False
    if last_reset is None:
        return True
    return last_reset != today
