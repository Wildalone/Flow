import os

from groq import BadRequestError, Groq, RateLimitError

MODEL = "openai/gpt-oss-20b"

SCENARIOS = {
    "prop_a": {
        "address": "42 Oak St",
        "nickname": "The Oak St Cottage",
        "booking_id": "bk_1001",
        "reset_instruction": (
            "If the client tells you to go ahead and remotely reset the lock: it WILL genuinely work. "
            "Report back that the reset succeeded and the guest is back in."
        ),
        "key_instruction": (
            "The backup key holder (Sam, the cleaner) responds quickly and shows up if you're told to contact them."
        ),
        "opening": "Hi, this is Alex from guest support — we've got a guest locked out at 42 Oak St (The Oak St Cottage). Wanted to loop you in — want me to try a remote lock reset?",
        "end_class": "resolved",
        "end_label": "Resolved",
        "resolution": "resolved_remote_reset",
        "end_summary": "Guest locked out at {address}. Client authorized a remote lock reset — it worked, guest is back in.",
    },
    "prop_b": {
        "address": "118 Maple Ave",
        "nickname": "Maple Loft",
        "booking_id": "bk_1002",
        "reset_instruction": (
            "The lock is actually offline. If the client tells you to try a remote reset, report back "
            "honestly that it did NOT work — the door's still locked, the lock isn't responding."
        ),
        "key_instruction": (
            "The backup key holder (Jordan, a neighbor) responds quickly and shows up if you're told to contact them."
        ),
        "opening": "Hi, this is Alex from guest support — guest's locked out at 118 Maple Ave (Maple Loft). Wanted to get your call on how to handle it.",
        "end_class": "resolved",
        "end_label": "Resolved",
        "resolution": "resolved_backup_key",
        "end_summary": "Guest locked out at {address}. Remote reset failed (lock offline) — client authorized dispatching the backup key holder, who responded and let the guest in.",
    },
    "prop_c": {
        "address": "7 Birch Court",
        "nickname": "Birch Court Bungalow",
        "booking_id": "bk_1003",
        "reset_instruction": (
            "There's no smart lock on this property at all. If the client suggests a remote reset, tell "
            "them there's nothing to reset here."
        ),
        "key_instruction": (
            "The backup key holder (Riley, the property manager) does NOT respond, no matter how many "
            "times you're told to follow up with them."
        ),
        "opening": "Hi, this is Alex from guest support — got a lockout at 7 Birch Court (Birch Court Bungalow), it's getting late for the guest. What do you want me to do?",
        "end_class": "escalated",
        "end_label": "Escalated — needs the client's personal follow-up",
        "resolution": "escalated_no_response",
        "end_summary": "Guest locked out at {address}. No smart lock on file, backup key holder unresponsive — escalated for the client to personally follow up.",
    },
}


def _client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Groq(api_key=api_key)


def _system_prompt(scenario: dict) -> str:
    return (
        "You are Alex, a guest-support agent messaging the CLIENT — the owner of a short-term rental "
        f"property at {scenario['address']} ({scenario['nickname']}) — about a guest lockout, to get "
        "their direction and coordinate a resolution.\n\n"
        "These instructions tell you exactly how to report outcomes — follow them precisely, don't "
        "invent an outcome that contradicts them:\n"
        f"- {scenario['reset_instruction']}\n"
        f"- {scenario['key_instruction']} If the client is told help is on the way but that person in "
        "fact doesn't respond, report that honestly rather than pretending it's handled.\n\n"
        "Keep messages short and natural, like a real work chat message (1-3 sentences), with no "
        "markdown and no function-call syntax of any kind — plain conversational text only. Never break "
        "character or mention that you are an AI, a model, or a simulation."
    )


def end_state(property_id: str) -> dict:
    scenario = SCENARIOS[property_id]
    return {
        "end_class": scenario["end_class"],
        "end_label": scenario["end_label"],
        "resolution": scenario["resolution"],
        "summary": scenario["end_summary"].format(address=scenario["address"]),
        "property_id": property_id,
        "booking_id": scenario["booking_id"],
    }


def guest_reply(property_id: str, history: list) -> str:
    scenario = SCENARIOS[property_id]
    client = _client()
    messages = [{"role": "system", "content": _system_prompt(scenario)}] + history
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=500,
            temperature=0.3,
            reasoning_effort="low",
            messages=messages,
        )
    except RateLimitError as e:
        raise RuntimeError(
            "Hit Groq's rate limit. Wait a bit and try again — see console.groq.com/settings/billing."
        ) from e
    except BadRequestError as e:
        raise RuntimeError(f"The model rejected that request: {e}") from e
    return response.choices[0].message.content or "..."
