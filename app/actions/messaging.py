from .registry import WRITE, register


@register(
    name="send_guest_message",
    kind=WRITE,
    description=(
        "Send a message to the guest (e.g. an apology, a status update, or resolution confirmation). "
        "This actually contacts the guest, so it requires host confirmation before running."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "guest_name": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["guest_name", "message"],
    },
)
def send_guest_message(guest_name: str, message: str) -> dict:
    return {"sent": True, "guest_name": guest_name, "message": message}
