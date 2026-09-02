"""Optional REST router for the SNC Intelligence Module.

This module is imported only when ``SNC_INTELLIGENCE_ENABLED=true``.  Keep all
Intelligence-specific imports here so the deterministic SNC core does not need
this package to start or run its tests.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from .clinical import ClinicalAnalyticsAgent
from .handover import ShiftHandoverAgent


def create_router(store) -> APIRouter:
    """Create the plugin router against the Core Event Store interface."""
    router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])
    clinical_agent = ClinicalAnalyticsAgent(
        frequent_window_hours=float(os.getenv("SNC_ANALYTICS_FREQUENT_WINDOW_HOURS", "4")),
        frequent_min_calls=int(os.getenv("SNC_ANALYTICS_FREQUENT_MIN_CALLS", "3")),
        baseline_days=int(os.getenv("SNC_ANALYTICS_BASELINE_DAYS", "7")),
    )
    handover_agent = ShiftHandoverAgent()

    @router.get("/clinical")
    def get_clinical_insights(window_hours: float = 24.0):
        """Return read-only frequent-caller and SLA-drift insights."""
        events = store.get_recent_events(500, source="real")
        return clinical_agent.analyze(events, window_hours=window_hours)

    @router.get("/handover")
    def get_shift_handover(shift: str = "morning", at: Optional[str] = None):
        """Return a read-only shift handover draft; it is never filed automatically."""
        if shift not in {name for name, _, _ in handover_agent.shifts}:
            raise HTTPException(status_code=400, detail="shift must be morning, afternoon, or night")
        if at:
            try:
                handover_at = datetime.fromisoformat(at)
                if handover_at.tzinfo is not None:
                    handover_at = handover_at.astimezone().replace(tzinfo=None)
            except ValueError:
                raise HTTPException(status_code=400, detail="at must be an ISO-8601 datetime")
        else:
            handover_at = datetime.now()
        events = store.get_recent_events(500, source="real")
        return handover_agent.generate(events, shift=shift, at=handover_at)

    return router
