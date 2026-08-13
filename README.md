# Lockout Flow

A host-facing assistant that closes the loop on one real short-term-rental operator headache: **a guest gets locked out mid-stay.**

The guided walkthrough at `/` steps through the flow one decision at a time: a guest message comes in, you pick how the agent responds, that reveals the guest's reply as the next set of options, and so on — branching through the happy path and every messy edge (offline lock, no smart lock on file, an unresponsive key holder, an address that doesn't match any booking) until the incident is logged and the guest is messaged. Every ending is real: reaching it writes an actual entry to the incident log.

There's also an AI chat prototype at `/chat` — a role-reversed roleplay where you play the host and a live Groq/Llama model plays the guest. Pick a scenario (online lock, offline lock, or no lock with an unresponsive key holder) and the AI stays grounded in that property's real state: tell it you've remotely reset a lock that's actually offline and it will push back instead of thanking you for a fix that didn't happen. It's the second iteration of this project's live-AI mode — the first was a tool-calling agent that decided which actions to take, which turned out to be too unreliable (rate limits, malformed tool calls, contradictory repeat actions) to depend on mid-recording. See the journey doc for that story.

Built with FastAPI. The guided walkthrough is a deterministic decision tree (no LLM calls, so it can't fail mid-demo); the chat prototype uses Groq (Llama 3.1 8B) for plain grounded chat completions — no tool-calling involved, so the malformed-function-call failure mode is structurally impossible. Both share the same mock property/booking data standing in for a real property-management system, and the same `/api/log-incident` endpoint for writing real incident records.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # only needed for the /chat AI prototype — add your GROQ_API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000 for the guided walkthrough (no API key required).

## Demo script

Start at `http://localhost:8000`. Click through at a natural pace:

1. **Guest message** — "locked out at 42 Oak St" — click **Continue** through the booking lookup.
2. **Branch point** — pick one of four options to show a different path:
   - **Lock is online** → remote reset → guest thanks you → resolved.
   - **Lock is offline** → backup key dispatched → key holder responds → resolved.
   - **No smart lock on file** → backup key dispatched → key holder does **not** respond → escalated, host told to call directly instead of a false all-clear.
   - **Address doesn't match a booking** → the agent asks for the correct address instead of guessing (try both a correction, which loops back into the flow, and staying unsure, which flags it for the host).
3. After any ending, use **Try another path** to jump straight to a different branch without retyping anything, or **Start over** for the full flow from the top.

Every ending shows a Resolved / Escalated / Needs-follow-up badge and confirms the incident was logged — check `data/incidents.json` afterward to see the real entries.

At `/chat`, pick a scenario, chat back and forth as the host, then click **Wrap up & log incident** whenever you're ready to conclude — it logs a real incident (resolution matched to that scenario's ground truth) and shows the same Resolved/Escalated badge as the walkthrough.

## Project layout

```
app/
  main.py          FastAPI app: serves both UIs, /api/log-incident (deterministic),
                   and /api/persona/* (the AI-plays-the-guest chat prototype)
  persona.py       Grounded guest-roleplay chat: per-scenario ground truth + explicit
                   reaction instructions, plain chat completion, no tool-calling at all
  agent.py         Earlier tool-calling agent prototype (kept for the journey doc's
                   story; no longer wired to a route)
  store.py         Loads/saves the mock JSON data
  actions/         One module per tool: booking lookup, lock status/reset, backup key dispatch,
                   incident logging, guest messaging — each registered via a small Action registry
data/              Mock properties, bookings, and the incident log the app writes to
static/            index.html + scenario.js — the guided walkthrough (primary)
                   chat.html + persona.js — the AI chat prototype
```
