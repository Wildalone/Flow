import os

from groq import BadRequestError, Groq, RateLimitError

MODEL = "openai/gpt-oss-20b"

SCENARIOS = {
    "prop_a": {
        "address": "42 Oak St",
        "nickname": "The Oak St Cottage",
        "booking_id": "bk_1001",
        "reset_instruction": (
            "If the agent tells you they're going to (or already did) remotely reset the lock: it WILL "
            "genuinely work. Once they report it, be relieved and thank them."
        ),
        "key_instruction": (
            "The backup key holder (Sam, the cleaner) responds quickly and shows up if the agent contacts them."
        ),
        "starter": "Hi, this is Alex from guest support — got a guest locked out at 42 Oak St. Want me to try a remote lock reset?",
        "end_class": "resolved",
        "end_label": "Resolved",
        "resolution": "resolved_remote_reset",
        "end_summary": "Guest locked out at {address}. Host authorized a remote lock reset — it worked, guest is back in.",
    },
    "prop_b": {
        "address": "118 Maple Ave",
        "nickname": "Maple Loft",
        "booking_id": "bk_1002",
        "reset_instruction": (
            "The lock is actually offline. If the agent says they're trying (or already tried) a remote "
            "reset, tell them it did NOT work — you can see the lock is still showing as locked/offline."
        ),
        "key_instruction": (
            "The backup key holder (Jordan, a neighbor) responds quickly and shows up if the agent contacts them."
        ),
        "starter": "Hi, this is Alex from guest support — guest's locked out at 118 Maple Ave. What do you want me to try?",
        "end_class": "resolved",
        "end_label": "Resolved",
        "resolution": "resolved_backup_key",
        "end_summary": "Guest locked out at {address}. Remote reset failed (lock offline) — host authorized dispatching the backup key holder, who responded and let the guest in.",
    },
    "prop_c": {
        "address": "7 Birch Court",
        "nickname": "Birch Court Bungalow",
        "booking_id": "bk_1003",
        "reset_instruction": (
            "There's no smart lock on this property at all. If the agent suggests a remote reset, tell "
            "them there's nothing to reset — it's a regular lock."
        ),
        "key_instruction": (
            "The backup key holder (Riley, the property manager) does NOT respond, no matter how many "
            "times the agent says they've reached out."
        ),
        "starter": "Hi, this is Alex from guest support — got a lockout at 7 Birch Court, it's getting late for the guest. What's the move?",
        "end_class": "escalated",
        "end_label": "Escalated — host following up personally",
        "resolution": "escalated_no_response",
        "end_summary": "Guest locked out at {address}. No smart lock on file, backup key holder unresponsive — host escalated to follow up personally.",
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
        "You are the property owner (the host) of a short-term rental at "
        f"{scenario['address']} ({scenario['nickname']}). A guest-support agent is messaging you about "
        "a guest lockout, asking for your direction and reporting back on what they've tried.\n\n"
        "These instructions tell you exactly how to react — follow them precisely, don't invent an "
        "outcome that contradicts them:\n"
        f"- {scenario['reset_instruction']}\n"
        f"- {scenario['key_instruction']} If the agent says help is on the way but that person in fact "
        "doesn't respond, grow a bit more concerned the longer it drags on rather than assuming it's fine.\n\n"
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


def host_reply(property_id: str, history: list) -> str:
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
