import os

from groq import BadRequestError, Groq, RateLimitError

MODEL = "llama-3.1-8b-instant"

SCENARIOS = {
    "prop_a": {
        "guest_name": "Priya Nandakumar",
        "address": "42 Oak St",
        "nickname": "The Oak St Cottage",
        "booking_id": "bk_1001",
        "reset_instruction": (
            "If the host says they've remotely reset the lock: it DID genuinely work — the door is now "
            "unlocked. Say so, be relieved, and thank them. Do not claim it's still locked."
        ),
        "key_instruction": (
            "The backup key holder (Sam, the cleaner) responds quickly and shows up if contacted."
        ),
        "opening": "Hi, I'm locked out of my rental at 42 Oak St! I've been standing outside for a few minutes now, can you help?",
        "end_class": "resolved",
        "end_label": "Resolved",
        "resolution": "resolved_remote_reset",
        "end_summary": "Guest {guest_name} was locked out at {address}. Smart lock was online — host resolved it with a remote reset.",
    },
    "prop_b": {
        "guest_name": "Marcus Webb",
        "address": "118 Maple Ave",
        "nickname": "Maple Loft",
        "booking_id": "bk_1002",
        "reset_instruction": (
            "The lock is actually offline. If the host says they've remotely reset it, that CANNOT have "
            "worked — the door is still locked no matter what they claim. Politely say it's still not "
            "opening, don't agree that it worked."
        ),
        "key_instruction": (
            "The backup key holder (Jordan, a neighbor) responds and shows up if contacted."
        ),
        "opening": "Hey, I can't get into my rental at 118 Maple Ave, the door won't budge. Please help!",
        "end_class": "resolved",
        "end_label": "Resolved",
        "resolution": "resolved_backup_key",
        "end_summary": "Guest {guest_name} was locked out at {address}. Lock was offline — backup key holder dispatched and responded, guest let in.",
    },
    "prop_c": {
        "guest_name": "Elena Torres",
        "address": "7 Birch Court",
        "nickname": "Birch Court Bungalow",
        "booking_id": "bk_1003",
        "reset_instruction": (
            "There is no smart lock on this property at all. If the host mentions resetting a lock "
            "remotely, point out there's no smart lock here to reset."
        ),
        "key_instruction": (
            "The backup key holder (Riley, the property manager) does NOT respond, no matter how long "
            "you wait or how many times the host says they've reached out."
        ),
        "opening": "Hi, I'm locked out at 7 Birch Court and it's getting late. Can someone help me get in?",
        "end_class": "escalated",
        "end_label": "Escalated — host notified to call directly",
        "resolution": "escalated_no_response",
        "end_summary": "Guest {guest_name} was locked out at {address}. No smart lock on file and backup key holder didn't respond — escalated for the host to call directly.",
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
        f"You are role-playing as {scenario['guest_name']}, a guest locked out of their short-term "
        f"rental at {scenario['address']} ({scenario['nickname']}). You are texting with the property "
        "host to get help.\n\n"
        "These instructions tell you exactly how to react — follow them precisely, don't improvise "
        "outcomes that contradict them:\n"
        f"- {scenario['reset_instruction']}\n"
        f"- {scenario['key_instruction']} If the host says help is on the way but they in fact don't "
        "respond, start neutral, then grow a bit more concerned the longer it drags on — don't invent "
        "a failure that hasn't been stated.\n\n"
        "Stay fully in character as the guest. Keep messages short and natural, like a real text message "
        "(1-3 sentences), with no markdown and no function-call syntax of any kind — plain conversational "
        "text only. Never break character or mention that you are an AI, a model, or a simulation."
    )


def end_state(property_id: str) -> dict:
    scenario = SCENARIOS[property_id]
    return {
        "end_class": scenario["end_class"],
        "end_label": scenario["end_label"],
        "resolution": scenario["resolution"],
        "summary": scenario["end_summary"].format(guest_name=scenario["guest_name"], address=scenario["address"]),
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
            max_tokens=200,
            temperature=0.3,
            messages=messages,
        )
    except RateLimitError as e:
        raise RuntimeError(
            "Hit Groq's rate limit. Wait a bit and try again — see console.groq.com/settings/billing."
        ) from e
    except BadRequestError as e:
        raise RuntimeError(f"The model rejected that request: {e}") from e
    return response.choices[0].message.content or "..."
