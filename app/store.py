import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str):
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(name: str, data) -> None:
    with open(DATA_DIR / name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_properties() -> list:
    return _load("properties.json")["properties"]


def load_bookings() -> list:
    return _load("bookings.json")["bookings"]


def find_property(property_id: str) -> dict:
    return next(p for p in load_properties() if p["id"] == property_id)


def append_incident(incident: dict) -> None:
    data = _load("incidents.json")
    data["incidents"].append(incident)
    _save("incidents.json", data)
