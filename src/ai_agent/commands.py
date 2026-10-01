from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def __init__(self, cwd: Path, allowlist: set[str] | None = None, timeout_seconds: int = 20):
        self.cwd = cwd
        self.allowlist = allowlist or {"python", "python3", "pytest", "npm", "node", "git"}
        self.timeout_seconds = timeout_seconds

    def run(self, command: list[str]) -> CommandResult:
        if not command:
            raise ValueError("empty command")
        executable = Path(command[0]).name
        if executable not in self.allowlist:
            raise PermissionError(f"command not allowed: {executable}")

        completed = subprocess.run(
            command,
            cwd=self.cwd,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        return CommandResult(
            command=tuple(command),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
