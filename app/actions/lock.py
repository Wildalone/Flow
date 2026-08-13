from ..store import find_property
from .registry import READ, WRITE, register


@register(
    name="check_lock_status",
    kind=READ,
    description="Check whether a property has a smart lock and, if so, whether it's currently online.",
    input_schema={
        "type": "object",
        "properties": {"property_id": {"type": "string"}},
        "required": ["property_id"],
    },
)
def check_lock_status(property_id: str) -> dict:
    prop = find_property(property_id)
    if prop is None:
        return {"error": "unknown_property_id", "property_id": property_id}
    if not prop["has_smart_lock"]:
        return {"has_smart_lock": False}
    return {"has_smart_lock": True, "lock_status": prop["lock_status"]}


@register(
    name="reset_smart_lock",
    kind=WRITE,
    description=(
        "Attempt to remotely reset/unlock a property's smart lock so the guest can get back in. "
        "Only succeeds if the lock is online. This changes real-world lock state, so it requires "
        "host confirmation before running."
    ),
    input_schema={
        "type": "object",
        "properties": {"property_id": {"type": "string"}},
        "required": ["property_id"],
    },
)
def reset_smart_lock(property_id: str) -> dict:
    prop = find_property(property_id)
    if prop is None:
        return {"success": False, "reason": "unknown_property_id"}
    if not prop["has_smart_lock"]:
        return {"success": False, "reason": "no_smart_lock"}
    if prop["lock_status"] != "online":
        return {"success": False, "reason": "lock_offline"}
    return {"success": True}
