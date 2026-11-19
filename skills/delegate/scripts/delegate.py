"""Manage persistent model routing settings for the delegate skill."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
DEFAULT_MAX_AGENTS = 3
HARD_MAX_AGENTS = 6


def catalog_models(catalog: Path) -> list[str]:
    candidates = [catalog, CODEX_HOME / "models_cache.json", CODEX_HOME / "models_cache.codex_work_desktop.json"]
    data = None
    for candidate in dict.fromkeys(candidates):
        if candidate.exists():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            break
    if data is None:
        result = subprocess.run(["codex", "debug", "models"], capture_output=True, text=True, timeout=30, check=True)
        data = json.loads(result.stdout)
    return [
        item["slug"]
        for item in data["models"]
        if item.get("visibility") == "list" and item.get("supported_in_api")
    ]


def valid_state(data: dict) -> dict:
    if data.get("version") == 1:
        data = {
            "version": 2,
            "mode": "manual",
            "models": data.get("models"),
            "max_agents": DEFAULT_MAX_AGENTS,
        }
    mode = data.get("mode")
    models = data.get("models")
    maximum = data.get("max_agents")
    if data.get("version") != 2 or mode not in ("auto", "manual"):
        raise ValueError("Invalid delegate state file")
    if not isinstance(models, list) or any(not isinstance(m, str) for m in models):
        raise ValueError("Invalid saved worker model list")
    if len(models) != len(set(models)):
        raise ValueError("Duplicate worker models in state file")
    if type(maximum) is not int or not 1 <= maximum <= HARD_MAX_AGENTS:
        raise ValueError("max_agents must be between 1 and 6")
    return {"version": 2, "mode": mode, "models": models, "max_agents": maximum}


def load_state(state: Path, legacy_config: Path) -> dict:
    if state.exists():
        return valid_state(json.loads(state.read_text(encoding="utf-8")))
    if legacy_config.exists():
        data = tomllib.loads(legacy_config.read_text(encoding="utf-8"))
        old_model = data.get("agents", {}).get("default_subagent_model")
        if old_model:
            return valid_state({"version": 2, "mode": "manual", "models": [old_model], "max_agents": DEFAULT_MAX_AGENTS})
    return valid_state({"version": 2, "mode": "auto", "models": [], "max_agents": DEFAULT_MAX_AGENTS})


def save_state(state: Path, data: dict) -> None:
    data = valid_state(data)
    state.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".delegate-", suffix=".json", dir=state.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, state)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    if valid_state(json.loads(state.read_text(encoding="utf-8"))) != data:
        raise ValueError("Saved delegate settings failed verification")


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
    parser.add_argument("--state", type=Path, default=CODEX_HOME / "delegate.json")
    parser.add_argument("--catalog", type=Path, default=CODEX_HOME / "models_cache.codex_work_desktop.json")
    parser.add_argument("--config", type=Path, default=CODEX_HOME / "config.toml")
    args = parser.parse_args()

    if args.command in ("models", "status", "manual", "reset") and args.values:
        parser.error(f"{args.command} takes no arguments")
    if args.command in ("select", "add", "remove", "count") and not args.values:
        parser.error(f"{args.command} requires an argument")

    if args.command == "models":
        print("\n".join(catalog_models(args.catalog)))
        return 0

    current = load_state(args.state, args.config)
    if args.command == "status":
        print(json.dumps(current))
        return 0

    updated = dict(current)
    if args.command == "reset":
        updated = {"version": 2, "mode": "auto", "models": [], "max_agents": DEFAULT_MAX_AGENTS}
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
        if args.command in ("select", "add"):
            available = catalog_models(args.catalog)
            unknown = [model for model in args.values if model not in available]
            if unknown:
                print("Unavailable model(s): " + ", ".join(unknown), file=sys.stderr)
                print("Selectable models: " + ", ".join(available), file=sys.stderr)
                return 2
        updated["mode"] = "manual"
        if args.command == "select":
            updated["models"] = list(dict.fromkeys(args.values))
        elif args.command == "add":
            updated["models"] = list(dict.fromkeys(current["models"] + args.values))
        else:
            updated["models"] = [model for model in current["models"] if model not in args.values]

    save_state(args.state, updated)
    print(json.dumps(load_state(args.state, args.config)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, tomllib.TOMLDecodeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"delegate: {exc}", file=sys.stderr)
        raise SystemExit(1)
