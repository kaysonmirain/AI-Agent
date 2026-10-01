from pathlib import Path

import pytest

from ai_agent.filesystem import FileTools, WorkspaceEscapeError, WorkspaceGuard


def test_write_preview_and_apply(tmp_path: Path) -> None:
    tools = FileTools(WorkspaceGuard.from_path(tmp_path))
    preview = tools.preview_write("notes.txt", "hello\n")
    assert preview.action == "write"
    assert "+hello" in preview.diff

    change = tools.write("notes.txt", "hello\n")
    assert change.path == "notes.txt"
    assert (tmp_path / "notes.txt").read_text() == "hello\n"


def test_workspace_escape_is_blocked(tmp_path: Path) -> None:
    tools = FileTools(WorkspaceGuard.from_path(tmp_path))
    with pytest.raises(WorkspaceEscapeError):
        tools.write("../outside.txt", "blocked\n")


def test_replace_requires_existing_text(tmp_path: Path) -> None:
    tools = FileTools(WorkspaceGuard.from_path(tmp_path))
    tools.write("app.py", "print('old')\n")
    change = tools.replace("app.py", "old", "new")
    assert "+print('new')" in change.diff
    with pytest.raises(ValueError):
        tools.replace("app.py", "missing", "value")
