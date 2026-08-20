# Lockout Flow

A host-facing assistant that closes the loop on one real short-term-rental operator headache: **a guest gets locked out mid-stay.**

The guided walkthrough at `/` steps through the flow one decision at a time: a support agent reaches out to you, the **property owner/client**, about a guest lockout — you pick how to direct the agent, that reveals the agent's next update as the next set of options, and so on — branching through the happy path and every messy edge (offline lock, no smart lock on file, an unresponsive key holder, an address that doesn't match any booking) until the incident is logged. Every ending is real: reaching it writes an actual entry to the incident log.

There's also an AI chat prototype at `/chat`: a live Groq model plays a guest-support **agent** messaging you, the **property owner**, about a lockout — asking for your direction and reporting outcomes. Pick a scenario (online lock, offline lock, or no lock with an unresponsive key holder) and the AI stays grounded in that property's real state: tell it to try a remote reset on a lock that's actually offline and it reports back honestly that it didn't work, instead of a false all-clear.

Built with FastAPI. The guided walkthrough is a deterministic decision tree (no LLM calls, so it can't fail mid-demo); the chat prototype uses Groq for plain grounded chat completions — no tool-calling involved. Both share the same mock property/booking data and the same `/api/log-incident` endpoint for writing real incident records.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # only needed for the /chat AI prototype — add your GROQ_API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000 for the guided walkthrough (no API key required).

## Demo script

Start at `http://localhost:8000`. Click through at a natural pace:

1. **Agent reaches out** about a lockout at 42 Oak St — click **Continue** to authorize the agent to look into it.
2. **Branch point** — pick one of four options to show a different path:
   - **Lock is online** → remote reset → client thanks the agent → resolved.
   - **Lock is offline** → backup key dispatched → key holder responds → resolved.
   - **No smart lock on file** → backup key dispatched → key holder does **not** respond → escalated, client follows up directly instead of a false all-clear.
   - **Address doesn't match a booking** → the agent asks the client to confirm the address instead of guessing (try both a correction, which loops back into the flow, and staying unsure, which flags it for follow-up).
3. After any ending, use **Try another path** to jump straight to a different branch without retyping anything, or **Start over** for the full flow from the top.

Every ending shows a Resolved / Escalated / Needs-follow-up badge and confirms the incident was logged — check `data/incidents.json` afterward to see the real entries.

At `/chat`, pick a scenario, chat back and forth as the property owner, then click **Wrap up & log incident** whenever you're ready to conclude — it logs a real incident (resolution matched to that scenario's ground truth) and shows the same Resolved/Escalated badge as the walkthrough.

## Project layout

```
app/
  main.py          FastAPI app: serves both UIs, /api/log-incident (deterministic),
                   and /api/persona/* (the AI-plays-the-agent chat prototype)
  persona.py       Grounded agent-roleplay chat: per-scenario ground truth + explicit
                   reporting instructions, plain chat completion, no tool-calling at all
  agent.py         Earlier tool-calling agent prototype (kept for the journey doc's
                   story; no longer wired to a route)
  store.py         Loads/saves the mock JSON data
  actions/         One module per tool: booking lookup, lock status/reset, backup key dispatch,
                   incident logging, guest messaging — each registered via a small Action registry
data/              Mock properties, bookings, and the incident log the app writes to
static/            index.html + scenario.js — the guided walkthrough (primary)
                   chat.html + persona.js — the AI chat prototype
```
