"""Irrigation queue management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class QueueItem:
    """Represents a single irrigation queue entry with Cycle & Soak tracking."""

    zone_id: str
    dauer_min: float
    cs_remaining: int  # 0 if no C&S active
    cs_pause_min: float
    started_at: datetime | None = None
