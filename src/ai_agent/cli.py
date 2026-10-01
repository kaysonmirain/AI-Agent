from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .agent import AgentSession


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AI Agent.")
    parser.add_argument("--workspace", required=True, help="Folder the agent can read and edit.")
    parser.add_argument("--task", required=True, help="Task to plan and execute.")
    parser.add_argument("--apply", action="store_true", help="Apply the file change instead of previewing it.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = AgentSession(args.workspace)
    record = session.run_task(args.task, apply=args.apply)
    if args.json:
        print(json.dumps(asdict(record), indent=2))
    else:
        for change in record.changes:
            print(f"{change['action'].upper()} {change['path']}")
            print(change["diff"] or "(no text diff)")
        print("applied:", record.applied)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
