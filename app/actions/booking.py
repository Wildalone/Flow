from ..store import load_bookings, load_properties
from .registry import READ, register


@register(
    name="lookup_booking",
    kind=READ,
    description=(
        "Find the active booking, guest, and property for an address or partial address "
        "the host typed. Returns found=False if there isn't exactly one matching property."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "address_query": {
                "type": "string",
                "description": "Address or partial address as reported by the host, e.g. '42 Oak St' or 'Maple'",
            }
        },
        "required": ["address_query"],
    },
)
def lookup_booking(address_query: str) -> dict:
    query = address_query.strip().lower()
    matches = [
        p
        for p in load_properties()
        if query in p["address"].lower() or query in p["nickname"].lower()
    ]
    if len(matches) != 1:
        return {
            "found": False,
            "match_count": len(matches),
            "message": "No single matching property found. Ask the host to confirm the exact address.",
        }

    prop = matches[0]
    booking = next(
        (b for b in load_bookings() if b["property_id"] == prop["id"] and b["status"] == "active"),
        None,
    )
    if booking is None:
        return {"found": False, "message": f"No active booking found for {prop['address']}."}

    return {"found": True, "property": prop, "booking": booking}
