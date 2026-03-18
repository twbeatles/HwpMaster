from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Protocol


class ActionHandler(Protocol):
    def run_action(self, action_id: str) -> bool:
        ...

    def execute_action(self, action_id: str, pset_name: str, values: dict[str, Any]) -> bool:
        ...


@dataclass
class ActionCommand:
    """Single action command."""

    action_type: str
    action_id: str
    pset_name: str = ""
    values: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def normalize(self) -> "ActionCommand":
        return ActionCommand(
            action_type=str(self.action_type or "").strip().lower(),
            action_id=str(self.action_id or "").strip(),
            pset_name=str(self.pset_name or "").strip(),
            values=dict(self.values or {}),
            description=str(self.description or "").strip(),
        )


@dataclass
class ActionTemplate:
    """Saved action template."""

    name: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    commands: list[ActionCommand] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["commands"] = [asdict(cmd) for cmd in self.commands]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionTemplate":
        cmds = [ActionCommand(**raw).normalize() for raw in data.get("commands", [])]
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            created_at=str(data.get("created_at", datetime.now().isoformat())),
            updated_at=str(data.get("updated_at", datetime.now().isoformat())),
            commands=cmds,
        )


@dataclass
class ActionPreset:
    """Built-in execute-action preset."""

    preset_id: str
    name: str
    category: str
    description: str = ""
    commands: list[ActionCommand] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "commands": [asdict(cmd) for cmd in self.commands],
        }
