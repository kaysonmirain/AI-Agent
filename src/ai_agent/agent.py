from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .commands import CommandRunner, CommandResult
from .filesystem import FileChange, FileTools, WorkspaceGuard


@dataclass
class AgentRecord:
    timestamp: str
    task: str
    applied: bool
    changes: list[dict] = field(default_factory=list)
    commands: list[dict] = field(default_factory=list)


class AgentSession:
    def __init__(self, workspace: str | Path):
        self.guard = WorkspaceGuard.from_path(workspace)
        self.files = FileTools(self.guard)
        self.commands = CommandRunner(self.guard.root)

    def run_task(self, task: str, apply: bool = False) -> AgentRecord:
        operation = self._plan(task)
        change = self._execute_file_operation(operation, apply=apply)
        record = AgentRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            task=task,
            applied=apply,
            changes=[asdict(change)],
        )
        self._write_audit(record)
        return record

    def run_check(self, command: list[str]) -> CommandResult:
        result = self.commands.run(command)
        record = AgentRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            task=f"run {' '.join(command)}",
            applied=True,
            commands=[asdict(result)],
        )
        self._write_audit(record)
        return result

    def _plan(self, task: str) -> dict:
        lowered = task.lower()
        if "append" in lowered:
            return {"action": "append", "path": self._extract_path(task), "content": self._content_from_task(task)}
        if "delete" in lowered:
            return {"action": "delete", "path": self._extract_path(task)}
        if "replace" in lowered and " with " in lowered:
            path = self._extract_path(task)
            old, new = task.split("replace", 1)[1].split(" with ", 1)
            return {"action": "replace", "path": path, "old": old.strip(), "new": new.strip()}
        return {"action": "write", "path": self._extract_path(task), "content": self._content_from_task(task)}

    def _execute_file_operation(self, operation: dict, apply: bool) -> FileChange:
        action = operation["action"]
        if action == "write":
            if apply:
                return self.files.write(operation["path"], operation["content"])
            return self.files.preview_write(operation["path"], operation["content"])
        if action == "append":
            if not apply:
                before = self.files.read(operation["path"]) if self.files.exists(operation["path"]) else ""
                return FileChange(operation["path"], "append", FileTools._diff(operation["path"], before, before + operation["content"]))
            return self.files.append(operation["path"], operation["content"])
        if action == "replace":
            if not apply:
                before = self.files.read(operation["path"])
                after = before.replace(operation["old"], operation["new"], 1)
                return FileChange(operation["path"], "replace", FileTools._diff(operation["path"], before, after))
            return self.files.replace(operation["path"], operation["old"], operation["new"])
        if action == "delete":
            if not apply:
                before = self.files.read(operation["path"]) if self.files.exists(operation["path"]) else ""
                return FileChange(operation["path"], "delete", FileTools._diff(operation["path"], before, ""))
            return self.files.delete(operation["path"])
        raise ValueError(f"unsupported action: {action}")

    @staticmethod
    def _extract_path(task: str) -> str:
        words = task.replace('"', " ").replace("'", " ").split()
        for word in words:
            if "." in word and "/" not in word[:1]:
                return word.strip(".,:;")
        return "agent_notes.md"

    @staticmethod
    def _content_from_task(task: str) -> str:
        if " with " in task.lower():
            content = task.split(" with ", 1)[1]
        elif ":" in task:
            content = task.split(":", 1)[1]
        else:
            content = task
        return content.strip() + "\n"

    def _write_audit(self, record: AgentRecord) -> None:
        run_dir = self.guard.root / ".agent" / "runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        stamp = record.timestamp.replace(":", "").replace("+", "Z")
        (run_dir / f"{stamp}.json").write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
