from pathlib import Path

from ai_agent.agent import AgentSession


def test_agent_previews_without_applying(tmp_path: Path) -> None:
    session = AgentSession(tmp_path)
    record = session.run_task("create plan.md with first note", apply=False)
    assert record.applied is False
    assert record.changes[0]["path"] == "plan.md"
    assert not (tmp_path / "plan.md").exists()


def test_agent_applies_and_writes_audit_log(tmp_path: Path) -> None:
    session = AgentSession(tmp_path)
    record = session.run_task("create plan.md with first note", apply=True)
    assert record.applied is True
    assert (tmp_path / "plan.md").read_text() == "first note\n"
    assert list((tmp_path / ".agent" / "runs").glob("*.json"))


def test_agent_blocks_command_not_on_allowlist(tmp_path: Path) -> None:
    session = AgentSession(tmp_path)
    try:
        session.run_check(["rm", "-rf", "anything"])
    except PermissionError as exc:
        assert "command not allowed" in str(exc)
    else:
        raise AssertionError("dangerous command was not blocked")
