from ..store import find_property
from .registry import WRITE, register


@register(
    name="dispatch_backup_key",
    kind=WRITE,
    description=(
        "Notify the property's backup-key holder (cleaner, neighbor, or property manager) to bring "
        "a physical key to the guest. This contacts a real person, so it requires host confirmation "
        "before running."
    ),
    input_schema={
        "type": "object",
        "properties": {"property_id": {"type": "string"}},
        "required": ["property_id"],
    },
)
def dispatch_backup_key(property_id: str) -> dict:
    prop = find_property(property_id)
    contact = prop["backup_key_contact"]
    if contact["responds"]:
        return {
            "dispatched": True,
            "acknowledged": True,
            "contact_name": contact["name"],
            "contact_phone": contact["phone"],
        }
    return {
        "dispatched": True,
        "acknowledged": False,
        "contact_name": contact["name"],
        "contact_phone": contact["phone"],
        "message": f"{contact['name']} did not respond. The host should call {contact['phone']} directly.",
    }
