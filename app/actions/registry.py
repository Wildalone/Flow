from dataclasses import dataclass
from typing import Callable

READ = "READ"
WRITE = "WRITE"


@dataclass
class Action:
    name: str
    kind: str
    description: str
    input_schema: dict
    handler: Callable


_actions: dict[str, Action] = {}


def register(name: str, kind: str, description: str, input_schema: dict):
    def decorator(func: Callable) -> Callable:
        _actions[name] = Action(
            name=name,
            kind=kind,
            description=description,
            input_schema=input_schema,
            handler=func,
        )
        return func

    return decorator


def get_action(name: str) -> Action:
    return _actions[name]


def tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": a.name,
                "description": a.description,
                "parameters": a.input_schema,
            },
        }
        for a in _actions.values()
    ]
