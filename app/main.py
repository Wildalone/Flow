import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent
from .actions import get_action

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Lockout Flow")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

SESSION: dict = {"messages": [], "pending": None}


class ChatRequest(BaseModel):
    message: str


class ConfirmRequest(BaseModel):
    approved: bool


class LogIncidentRequest(BaseModel):
    summary: str
    resolution: str
    property_id: str | None = None
    booking_id: str | None = None


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/chat")
def chat_page():
    return FileResponse(BASE_DIR / "static" / "chat.html")


@app.post("/api/log-incident")
def log_incident_endpoint(req: LogIncidentRequest):
    result = get_action("log_incident").handler(
        summary=req.summary,
        resolution=req.resolution,
        property_id=req.property_id,
        booking_id=req.booking_id,
    )
    return result


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/reset")
def reset():
    SESSION["messages"] = []
    SESSION["pending"] = None
    return {"reset": True}


@app.post("/api/chat")
def chat(req: ChatRequest):
    if SESSION["pending"] is not None:
        return JSONResponse(
            {"error": "There's a pending action awaiting confirmation. Confirm or cancel it first."},
            status_code=409,
        )
    SESSION["messages"].append({"role": "user", "content": req.message})
    try:
        result = agent.run_turn(SESSION["messages"])
    except RuntimeError as e:
        SESSION["messages"].pop()
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        SESSION["messages"].pop()
        logging.exception("Unexpected error in /api/chat")
        return JSONResponse(
            {"error": "Something unexpected went wrong handling that message. Try rephrasing, or click Reset demo."},
            status_code=500,
        )
    SESSION["messages"] = result["messages"]
    return _respond(result)


@app.post("/api/confirm")
def confirm(req: ConfirmRequest):
    pending = SESSION["pending"]
    if pending is None:
        return JSONResponse({"error": "No pending action."}, status_code=400)
    try:
        result = agent.resolve_pending(
            SESSION["messages"],
            tool_call_id=pending["tool_call_id"],
            action_name=pending["action_name"],
            action_input=pending["action_input"],
            approved=req.approved,
            prior_tool_results=pending["prior_tool_results"],
        )
    except RuntimeError as e:
        # The action itself already ran inside resolve_pending before the follow-up
        # model call failed, so clear the pending state rather than leaving it stuck.
        SESSION["pending"] = None
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        SESSION["pending"] = None
        logging.exception("Unexpected error in /api/confirm")
        return JSONResponse(
            {"error": "Something unexpected went wrong completing that action. Try rephrasing, or click Reset demo."},
            status_code=500,
        )
    SESSION["messages"] = result["messages"]
    return _respond(result)


def _respond(result: dict):
    if result["type"] == "pending_action":
        SESSION["pending"] = {
            "tool_call_id": result["tool_call_id"],
            "action_name": result["action_name"],
            "action_input": result["action_input"],
            "prior_tool_results": result["prior_tool_results"],
        }
        return {
            "type": "pending_action",
            "action_name": result["action_name"],
            "action_input": result["action_input"],
        }
    SESSION["pending"] = None
    return {"type": "text", "text": result["text"]}
