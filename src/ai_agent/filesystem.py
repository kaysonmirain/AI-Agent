from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from pathlib import Path


class WorkspaceEscapeError(ValueError):
    """Raised when a requested path leaves the active workspace."""


@dataclass(frozen=True)
class WorkspaceGuard:
    root: Path

    @classmethod
    def from_path(cls, root: str | os.PathLike[str]) -> "WorkspaceGuard":
        path = Path(root).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return cls(path)

    def resolve(self, relative_path: str | os.PathLike[str]) -> Path:
        candidate = (self.root / Path(relative_path)).expanduser().resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise WorkspaceEscapeError(f"path escapes workspace: {relative_path}")
        return candidate


@dataclass
class FileChange:
    path: str
    action: str
    diff: str


class FileTools:
    def __init__(self, guard: WorkspaceGuard):
        self.guard = guard

    def read(self, path: str) -> str:
        return self.guard.resolve(path).read_text(encoding="utf-8")

    def exists(self, path: str) -> bool:
        return self.guard.resolve(path).exists()

    def preview_write(self, path: str, content: str) -> FileChange:
        target = self.guard.resolve(path)
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        return FileChange(path=path, action="write", diff=self._diff(path, before, content))

    def write(self, path: str, content: str) -> FileChange:
        change = self.preview_write(path, content)
        target = self.guard.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return change

    def append(self, path: str, content: str) -> FileChange:
        target = self.guard.resolve(path)
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        next_text = before + content
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(next_text, encoding="utf-8")
        return FileChange(path=path, action="append", diff=self._diff(path, before, next_text))

    def replace(self, path: str, old: str, new: str) -> FileChange:
        target = self.guard.resolve(path)
        before = target.read_text(encoding="utf-8")
        if old not in before:
            raise ValueError(f"replacement text not found in {path}")
        next_text = before.replace(old, new, 1)
        target.write_text(next_text, encoding="utf-8")
        return FileChange(path=path, action="replace", diff=self._diff(path, before, next_text))

    def delete(self, path: str) -> FileChange:
        target = self.guard.resolve(path)
        before = target.read_text(encoding="utf-8") if target.exists() and target.is_file() else ""
        if target.is_dir():
            raise IsADirectoryError(f"refusing to delete directory through file tool: {path}")
        if target.exists():
            target.unlink()
        return FileChange(path=path, action="delete", diff=self._diff(path, before, ""))

    @staticmethod
    def _diff(path: str, before: str, after: str) -> str:
        return "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
