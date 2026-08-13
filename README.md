# Lockout Flow

A host-facing assistant that closes the loop on one real short-term-rental operator headache: **a guest gets locked out mid-stay.**

Tell it what's happening in plain language, and it looks up the booking, resolves access (remote lock reset or dispatching a backup key), logs the incident, and drafts the guest follow-up — asking for your confirmation before anything that actually acts in the real world (resetting a lock, contacting the key holder, messaging the guest).

Built with Groq (Llama 3.3 70B, OpenAI-compatible tool calling) + FastAPI, with a small mock dataset standing in for a real property-management system.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then add your GROQ_API_KEY
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Demo script (the messy edges)

The mock data has three properties, each set up to trigger a different path:

| Type in the chat | Property | What happens |
|---|---|---|
| `Guest at 42 Oak St is locked out` | Oak St Cottage — smart lock, online | Remote reset resolves it immediately |
| `Guest at 118 Maple Ave can't get in` | Maple Loft — smart lock, offline | Reset fails, falls back to dispatching the backup key holder (who responds) |
| `Locked out at 7 Birch Court` | Birch Court Bungalow — no smart lock | Goes straight to the backup key holder — who does **not** respond, so the incident is logged as escalated and you're told to call them directly |
| `Guest locked out at 99 Nowhere Ln` | no match | No booking found — the assistant asks you to confirm the address instead of guessing |

Every write action (lock reset, key dispatch, incident log, guest message) shows up as a confirm/cancel card before it runs. Click **Reset demo** between runs to clear the conversation.

## Project layout

```
app/
  main.py          FastAPI app: serves the UI, /api/chat, /api/confirm, /api/reset
  agent.py         Groq tool-use loop (READ actions auto-run, WRITE actions wait for confirmation)
  store.py         Loads/saves the mock JSON data
  actions/         One module per tool: booking lookup, lock status/reset, backup key dispatch,
                   incident logging, guest messaging — each registered via a small Action registry
data/              Mock properties, bookings, and the incident log the app writes to
static/            Chat UI (vanilla HTML/CSS/JS, no build step)
```
