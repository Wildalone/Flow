import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import persona
from .actions import get_action

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Lockout Flow")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

PERSONA_SESSION: dict = {"property_id": None, "history": []}


class LogIncidentRequest(BaseModel):
    summary: str
    resolution: str
    property_id: str | None = None
    booking_id: str | None = None


class PersonaStartRequest(BaseModel):
    property_id: str


class PersonaReplyRequest(BaseModel):
    message: str


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


@app.get("/api/persona/scenarios")
def persona_scenarios():
    return {
        pid: {"address": s["address"], "nickname": s["nickname"]}
        for pid, s in persona.SCENARIOS.items()
    }


@app.post("/api/persona/start")
def persona_start(req: PersonaStartRequest):
    scenario = persona.SCENARIOS.get(req.property_id)
    if scenario is None:
        return JSONResponse({"error": "Unknown scenario."}, status_code=400)
    PERSONA_SESSION["property_id"] = req.property_id
    PERSONA_SESSION["history"] = []
    return {"address": scenario["address"], "starter": scenario["starter"]}


@app.post("/api/persona/reply")
def persona_reply(req: PersonaReplyRequest):
    if PERSONA_SESSION["property_id"] is None:
        return JSONResponse({"error": "No active scenario. Pick one to start."}, status_code=400)
    PERSONA_SESSION["history"].append({"role": "user", "content": req.message})
    try:
        reply = persona.host_reply(PERSONA_SESSION["property_id"], PERSONA_SESSION["history"])
    except RuntimeError as e:
        PERSONA_SESSION["history"].pop()
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        PERSONA_SESSION["history"].pop()
        logging.exception("Unexpected error in /api/persona/reply")
        return JSONResponse(
            {"error": "Something went wrong generating the host's reply. Try again."}, status_code=500
        )
    PERSONA_SESSION["history"].append({"role": "assistant", "content": reply})
    return {"reply": reply}


@app.post("/api/persona/end")
def persona_end():
    if PERSONA_SESSION["property_id"] is None:
        return JSONResponse({"error": "No active scenario."}, status_code=400)
    state = persona.end_state(PERSONA_SESSION["property_id"])
    get_action("log_incident").handler(
        summary=state["summary"],
        resolution=state["resolution"],
        property_id=state["property_id"],
        booking_id=state["booking_id"],
    )
    PERSONA_SESSION["property_id"] = None
    PERSONA_SESSION["history"] = []
    return {"end_class": state["end_class"], "end_label": state["end_label"]}


@app.post("/api/persona/reset")
def persona_reset():
    PERSONA_SESSION["property_id"] = None
    PERSONA_SESSION["history"] = []
    return {"reset": True}
