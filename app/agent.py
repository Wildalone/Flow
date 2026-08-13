import json
import os

from groq import BadRequestError, Groq, RateLimitError

from .actions import WRITE, get_action, tool_schemas

SYSTEM_PROMPT = """You are an assistant helping a short-term-rental host resolve a guest lockout, start to finish.

When the host describes a lockout situation:
1. Look up the booking from whatever address or details the host gave you.
2. Check the property's lock status.
3. Resolve access: try a remote lock reset if the lock is online; if it's offline or there's no smart lock, dispatch the backup key holder instead.
Two closing steps are mandatory and non-negotiable, in this order, no matter how the lockout was resolved (even if it's still escalated/unresolved):
4. Log the incident (log_incident) — always, exactly once.
5. Draft and send a short, warm message to the guest (send_guest_message) — always, exactly once, confirming the resolution or explaining what happens next if it's still unresolved.

Handle messy edges honestly instead of guessing:
- If a booking lookup doesn't find a single match, do NOT retry with a reworded or more detailed address — the data won't change. Immediately stop and ask the host to confirm the exact address instead.
- If dispatching the backup key holder gets no response, do not claim the lockout is resolved. Still complete steps 4 and 5 above, logging it as escalated and telling the guest and host that the host will call the contact directly.
- Narrate what you're doing in one short line before each step, then act. Keep replies concise.
"""

MAX_STEPS = 8
MODEL = "llama-3.3-70b-versatile"


def _client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Groq(api_key=api_key)


def _stringify(result) -> str:
    return json.dumps(result)


def _call_model(client: Groq, messages: list):
    return client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        temperature=0.2,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        tools=tool_schemas(),
    )


CLARIFY_AFTER_FAILED_LOOKUPS = 2
CLARIFY_TEXT = (
    "I couldn't find a matching booking for that address after a couple of tries. "
    "Could you double-check it against the exact address on the reservation?"
)

REQUIRED_CLOSING_ACTIONS = {"log_incident", "send_guest_message"}


def _called_actions(messages: list) -> set:
    names = set()
    for m in messages:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            names.update(tc["function"]["name"] for tc in m["tool_calls"])
    return names


def _had_successful_lookup(messages: list) -> bool:
    for m in messages:
        if m.get("role") != "tool":
            continue
        try:
            content = json.loads(m["content"])
        except (TypeError, ValueError):
            continue
        if isinstance(content, dict) and content.get("found") and "booking" in content:
            return True
    return False


def run_turn(messages: list) -> dict:
    """Advance the conversation until the model produces plain text or stages a
    WRITE action. Returns a dict with type "text" or "pending_action"."""
    client = _client()
    messages = list(messages)
    failed_lookups = 0
    nudged_incomplete = False

    for _ in range(MAX_STEPS):
        try:
            response = _call_model(client, messages)
        except RateLimitError as e:
            raise RuntimeError(
                "Hit Groq's rate limit (likely the free-tier daily token cap). "
                "Wait a bit and try again — see console.groq.com/settings/billing for details."
            ) from e
        except BadRequestError as e:
            if "tool_use_failed" not in str(e):
                raise
            # Llama occasionally emits malformed inline function-call syntax that
            # Groq rejects outright. Nudge it once and retry before giving up.
            nudge = messages + [
                {
                    "role": "system",
                    "content": (
                        "Your previous turn used malformed function-call syntax. Call at most "
                        "one tool per turn using the tool-calling mechanism only — never write "
                        "a function call as plain text."
                    ),
                }
            ]
            try:
                response = _call_model(client, nudge)
            except BadRequestError:
                return {
                    "type": "text",
                    "text": "I hit a hiccup working through that step. Could you rephrase or repeat what's going on?",
                    "messages": messages,
                }
        choice = response.choices[0].message
        tool_calls = choice.tool_calls or []

        assistant_msg = {"role": "assistant", "content": choice.content}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            missing = REQUIRED_CLOSING_ACTIONS - _called_actions(messages)
            if missing and _had_successful_lookup(messages) and not nudged_incomplete:
                # The model sometimes narrates a closing step (e.g. "the guest has been
                # notified") without actually calling the tool. Give it one corrective
                # nudge before accepting the final answer.
                nudged_incomplete = True
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "You haven't actually called "
                            + ", ".join(sorted(missing))
                            + " yet — those are mandatory. Call them now before replying with plain text."
                        ),
                    }
                )
                continue
            return {"type": "text", "text": choice.content or "", "messages": messages}

        tool_results = []
        pending = None
        for tc in tool_calls:
            action = get_action(tc.function.name)
            args = json.loads(tc.function.arguments or "{}")
            if action.kind == WRITE:
                if pending is None:
                    pending = (tc, args)
                else:
                    # A second write requested in the same turn: defer it too,
                    # rather than executing it without confirmation.
                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": _stringify(
                                {"deferred": True, "reason": "awaiting confirmation of a prior action first"}
                            ),
                        }
                    )
                continue
            result = action.handler(**args)
            if tc.function.name == "lookup_booking" and not result.get("found"):
                failed_lookups += 1
            tool_results.append(
                {"role": "tool", "tool_call_id": tc.id, "content": _stringify(result)}
            )

        if pending is not None:
            pending_tc, pending_args = pending
            return {
                "type": "pending_action",
                "tool_call_id": pending_tc.id,
                "action_name": pending_tc.function.name,
                "action_input": pending_args,
                "prior_tool_results": tool_results,
                "messages": messages,
            }

        messages.extend(tool_results)

        if failed_lookups >= CLARIFY_AFTER_FAILED_LOOKUPS:
            # Llama tends to retry lookup_booking with reworded addresses instead of
            # stopping, which burns the whole step budget. Short-circuit deterministically
            # rather than relying on the model to notice on its own.
            messages.append({"role": "assistant", "content": CLARIFY_TEXT})
            return {"type": "text", "text": CLARIFY_TEXT, "messages": messages}

    return {
        "type": "text",
        "text": "I've hit my step limit for this turn — let me know how you'd like to continue.",
        "messages": messages,
    }


def resolve_pending(
    messages: list,
    tool_call_id: str,
    action_name: str,
    action_input: dict,
    approved: bool,
    prior_tool_results: list,
) -> dict:
    if approved:
        result = get_action(action_name).handler(**action_input)
    else:
        result = {"cancelled_by_host": True}

    tool_results = list(prior_tool_results) + [
        {"role": "tool", "tool_call_id": tool_call_id, "content": _stringify(result)}
    ]
    messages = list(messages) + tool_results
    return run_turn(messages)
