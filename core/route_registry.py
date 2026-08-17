from __future__ import annotations

from typing import Any, Dict, List


class RouteRegistry:
    """Simple registry to document the modular surface layout and supported routes."""

    def __init__(self) -> None:
        self.routes: List[Dict[str, Any]] = [
            {"method": "GET", "path": "/health", "purpose": "System health and backend readiness"},
            {"method": "GET", "path": "/api/events", "purpose": "Recent event feed"},
            {"method": "POST", "path": "/api/events/trigger", "purpose": "Synthetic test trigger"},
            {"method": "POST", "path": "/api/events/acknowledge/{room_id}", "purpose": "Acknowledge room call"},
            {"method": "POST", "path": "/api/events/clear/{room_id}", "purpose": "Clear room call"},
            {"method": "GET", "path": "/api/analytics/kpi", "purpose": "KPI summary"},
            {"method": "GET", "path": "/downloads", "purpose": "Service portal and installer downloads"},
            {"method": "GET", "path": "/ws/nurse-station", "purpose": "Real-time nurse station websocket"},
        ]

    def list_routes(self) -> List[Dict[str, Any]]:
        return self.routes
