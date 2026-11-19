"""Manage persistent Delegate settings for Claude Code."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


CLAUDE_HOME = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
MODELS = ("haiku", "sonnet", "opus")
DEFAULT_MAX_AGENTS = 3
HARD_MAX_AGENTS = 6


def valid_state(data: dict) -> dict:
    mode = data.get("mode")
    models = data.get("models")
    maximum = data.get("max_agents")
    if data.get("version") != 1 or mode not in ("auto", "manual"):
        raise ValueError("Invalid Delegate settings")
    if not isinstance(models, list) or any(model not in MODELS for model in models):
        raise ValueError("Manual models must be haiku, sonnet, or opus")
    if len(models) != len(set(models)):
        raise ValueError("Duplicate manual models")
    if type(maximum) is not int or not 1 <= maximum <= HARD_MAX_AGENTS:
        raise ValueError("max_agents must be between 1 and 6")
    return {"version": 1, "mode": mode, "models": models, "max_agents": maximum}


def load_state(path: Path) -> dict:
    if path.exists():
        return valid_state(json.loads(path.read_text(encoding="utf-8")))
    return {"version": 1, "mode": "auto", "models": [], "max_agents": DEFAULT_MAX_AGENTS}


def save_state(path: Path, data: dict) -> None:
    data = valid_state(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".delegate-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    if load_state(path) != data:
        raise ValueError("Saved settings failed verification")


def positive_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as exc:
        raise ValueError("Agent count must be between 1 and 6") from exc
    if not 1 <= count <= HARD_MAX_AGENTS:
        raise ValueError("Agent count must be between 1 and 6")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("models", "status", "select", "add", "remove", "auto", "manual", "count", "reset"))
    parser.add_argument("values", nargs="*")
    parser.add_argument("--state", type=Path, default=CLAUDE_HOME / "delegate.json")
    args = parser.parse_args()

    if args.command in ("models", "status", "manual", "reset") and args.values:
        parser.error(f"{args.command} takes no arguments")
    if args.command in ("select", "add", "remove", "count") and not args.values:
        parser.error(f"{args.command} requires an argument")
    if args.command == "models":
        print("\n".join(MODELS))
        return 0

    current = load_state(args.state)
    if args.command == "status":
        print(json.dumps(current))
        return 0

    updated = dict(current)
    if args.command == "reset":
        updated = {"version": 1, "mode": "auto", "models": [], "max_agents": DEFAULT_MAX_AGENTS}
    elif args.command == "manual":
        if not current["models"]:
            raise ValueError("No saved manual models; use select <model> first")
        updated["mode"] = "manual"
    elif args.command == "count":
        if len(args.values) != 1:
            parser.error("count requires exactly one number")
        updated["max_agents"] = positive_count(args.values[0])
    elif args.command == "auto" or (args.command == "select" and args.values[0] == "auto"):
        counts = args.values if args.command == "auto" else args.values[1:]
        if len(counts) > 1:
            parser.error("auto accepts at most one agent count")
        updated["mode"] = "auto"
        if counts:
            updated["max_agents"] = positive_count(counts[0])
    else:
        if args.command in ("select", "add") and any(model not in MODELS for model in args.values):
            raise ValueError("Manual models must be haiku, sonnet, or opus")
        updated["mode"] = "manual"
        if args.command == "select":
            updated["models"] = list(dict.fromkeys(args.values))
        elif args.command == "add":
            updated["models"] = list(dict.fromkeys(current["models"] + args.values))
        else:
            updated["models"] = [model for model in current["models"] if model not in args.values]

    save_state(args.state, updated)
    print(json.dumps(load_state(args.state)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"delegate: {exc}", file=sys.stderr)
        raise SystemExit(1)
