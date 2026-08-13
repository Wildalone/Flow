# Lockout Flow

A host-facing assistant that closes the loop on one real short-term-rental operator headache: **a guest gets locked out mid-stay.**

The guided walkthrough at `/` steps through the flow one decision at a time: a guest message comes in, you pick how the agent responds, that reveals the guest's reply as the next set of options, and so on — branching through the happy path and every messy edge (offline lock, no smart lock on file, an unresponsive key holder, an address that doesn't match any booking) until the incident is logged and the guest is messaged. Every ending is real: reaching it writes an actual entry to the incident log.

There's also an AI chat prototype at `/chat` — free-form text, driven live by a Groq/Llama tool-calling agent that decides which actions to take and asks for confirmation before anything with a real-world effect. It's the earlier, more ambitious version of this project; see the journey doc for why the guided walkthrough became the primary demo instead (short version: a live third-party model call is the wrong thing to depend on mid-recording).

Built with FastAPI. The guided walkthrough is a deterministic decision tree (no LLM calls, so it can't fail mid-demo); the chat prototype uses Groq (Llama 3.1 8B, OpenAI-compatible tool calling). Both share the same action registry and mock property/booking data standing in for a real property-management system.

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

## Project layout

```
app/
  main.py          FastAPI app: serves both UIs, /api/log-incident (deterministic),
                   and /api/chat, /api/confirm, /api/reset (AI prototype)
  agent.py         Groq tool-use loop for the /chat prototype (READ actions auto-run,
                   WRITE actions wait for confirmation)
  store.py         Loads/saves the mock JSON data
  actions/         One module per tool: booking lookup, lock status/reset, backup key dispatch,
                   incident logging, guest messaging — each registered via a small Action registry
data/              Mock properties, bookings, and the incident log the app writes to
static/            index.html + scenario.js — the guided walkthrough (primary)
                   chat.html + app.js — the AI chat prototype
```
