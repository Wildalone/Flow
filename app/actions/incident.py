from datetime import datetime, timezone

from ..store import append_incident
from .registry import WRITE, register


@register(
    name="log_incident",
    kind=WRITE,
    description=(
        "Record this lockout incident to the host's incident log for their records. Always do this "
        "once the situation is resolved or escalated."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "property_id": {"type": "string"},
            "booking_id": {"type": "string"},
            "summary": {
                "type": "string",
                "description": "One or two sentence summary of what happened and how it was resolved or escalated",
            },
            "resolution": {
                "type": "string",
                "enum": [
                    "resolved_remote_reset",
                    "resolved_backup_key",
                    "escalated_no_response",
                    "escalated_no_booking_match",
                ],
            },
        },
        "required": ["summary", "resolution"],
    },
)
def log_incident(
    summary: str,
    resolution: str,
    property_id: str | None = None,
    booking_id: str | None = None,
) -> dict:
    incident = {
        "property_id": property_id,
        "booking_id": booking_id,
        "summary": summary,
        "resolution": resolution,
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    append_incident(incident)
    return {"logged": True}
