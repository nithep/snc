"""Deterministic shift handover draft generator for SNC."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, time, timedelta
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .clinical import parse_timestamp


DEFAULT_SHIFTS: Tuple[Tuple[str, time, time], ...] = (
    ("morning", time(7, 0), time(15, 0)),
    ("afternoon", time(15, 0), time(23, 0)),
    ("night", time(23, 0), time(7, 0)),
)


class ShiftHandoverAgent:
    """Aggregate persisted events into a draft that a human must review."""

    def __init__(self, shifts: Tuple[Tuple[str, time, time], ...] = DEFAULT_SHIFTS):
        self.shifts = shifts

    def _window(self, at: datetime, shift_name: str) -> Tuple[datetime, datetime]:
        for name, start, end in self.shifts:
            if name != shift_name:
                continue
            start_date = at.date()
            if start < end:
                start_dt = datetime.combine(start_date, start)
                end_dt = datetime.combine(start_date, end)
                if at < start_dt:
                    start_dt -= timedelta(days=1)
                    end_dt -= timedelta(days=1)
            else:
                start_dt = datetime.combine(start_date, start)
                end_dt = datetime.combine(start_date + timedelta(days=1), end)
                if at < start_dt:
                    start_dt -= timedelta(days=1)
                    end_dt -= timedelta(days=1)
            return start_dt, end_dt
        raise ValueError(f"unknown shift: {shift_name}")

    def generate(
        self,
        events: Iterable[Mapping[str, Any]],
        *,
        shift: str,
        at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Create a read-only draft for one configured shift."""
        at = at or datetime.now()
        start, end = self._window(at, shift)
        selected = [
            event for event in events
            if (timestamp := parse_timestamp(event.get("timestamp"))) is not None
            and start <= timestamp < end
        ]
        completed = [event for event in selected if event.get("status") == "resolved"]
        ack_values = [
            float(event["ack_time_seconds"])
            for event in completed
            if event.get("ack_time_seconds") is not None
        ]
        resolution_values = [
            float(event["resolution_time_seconds"])
            for event in completed
            if event.get("resolution_time_seconds") is not None
        ]
        room_counts = Counter(str(event.get("room_id", "")).zfill(4) for event in selected)
        open_cases = [
            {
                "room_id": str(event.get("room_id", "")).zfill(4),
                "event_type": event.get("event_type"),
                "status": event.get("status"),
                "created_at": event.get("timestamp"),
            }
            for event in selected
            if event.get("status") in {"active", "acknowledged"}
        ]
        watch_rooms = [
            {"room_id": room_id, "call_count": count}
            for room_id, count in room_counts.most_common()
            if count > 1
        ]

        return {
            "agent": "shift-handover",
            "mode": "rule-based",
            "status": "draft",
            "generated_at": at.isoformat(),
            "shift": {
                "name": shift,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "summary": {
                "total_cases": len(selected),
                "completed_cases": len(completed),
                "open_cases": len(open_cases),
                "emergency_cases": sum(
                    1 for event in selected if event.get("event_type") == "CALL_BATHROOM_EMERGENCY"
                ),
                "avg_ack_time_seconds": round(mean(ack_values), 2) if ack_values else None,
                "avg_resolution_time_seconds": round(mean(resolution_values), 2)
                if resolution_values else None,
                "sla_breached_cases": sum(1 for event in completed if event.get("sla_breached")),
            },
            "rooms_to_watch": watch_rooms,
            "open_cases": open_cases,
            "event_types": dict(Counter(str(event.get("event_type", "UNKNOWN")) for event in selected)),
            "safety": {
                "read_only": True,
                "draft_only": True,
                "requires_human_review": True,
                "filed": False,
            },
        }
