from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ApprovalInbox:
    """Tracks manual approval for high-risk PBX or hardware actions."""

    def __init__(self) -> None:
        self._requests: Dict[str, Dict[str, Any]] = {}

    def create_request(self, action: str, details: str, actor: str = "operator") -> Dict[str, Any]:
        request_id = f"approval-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        payload = {
            "id": request_id,
            "action": action,
            "details": details,
            "risk": "critical",
            "actor": actor,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._requests[request_id] = payload
        return payload

    def resolve_request(self, request_id: str, approved: bool, reviewer: str = "system") -> Optional[Dict[str, Any]]:
        request = self._requests.get(request_id)
        if request is None:
            return None
        request["status"] = "approved" if approved else "rejected"
        request["reviewer"] = reviewer
        request["updated_at"] = datetime.now(timezone.utc).isoformat()
        return request

    def list_requests(self) -> List[Dict[str, Any]]:
        return list(self._requests.values())
