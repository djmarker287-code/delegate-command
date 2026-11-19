"""Local Delegate task checkpoint and accounting helper (no agent API calls)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
PLATFORM = "codex"
RUNS = HOME / "delegate-runs"
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
PRIORITIES = ("balanced", "speed", "cost", "quality")
OUTCOMES = ("success", "failed", "blocked")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def write_json(path: Path, data: dict) -> None:
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


def run_path(directory: Path, identifier: str) -> Path:
    if not IDENTIFIER.fullmatch(identifier):
        raise ValueError("Invalid run ID")
    return directory / f"{identifier}.json"


def read_run(directory: Path, identifier: str) -> dict:
    path = run_path(directory, identifier)
    if not path.exists():
        raise ValueError(f"Run {identifier} does not exist")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("id") != identifier:
        raise ValueError("Invalid run checkpoint")
    return data


def nonnegative_float(value: str) -> float:
    number = float(value)
    if not 0 <= number < float("inf"):
        raise ValueError("Amount must be a finite nonnegative number")
    return number


def nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise ValueError("Tokens must be nonnegative")
    return number


def known_int(value: str) -> int | None:
    return None if value == "unknown" else nonnegative_int(value)


def known_float(value: str) -> float | None:
    return None if value == "unknown" else nonnegative_float(value)


def optional_positive_int(value: str | None) -> int | None:
    if value is None:
        return None
    number = int(value)
    if number <= 0:
        raise ValueError("Budget must be positive")
    return number


def optional_positive_float(value: str | None) -> float | None:
    if value is None:
        return None
    number = nonnegative_float(value)
    if number == 0:
        raise ValueError("Budget must be positive")
    return number


def settings(home: Path) -> dict:
    path = home / "delegate.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    maximum = data.get("max_agents", 3)
    priority = data.get("priority", "balanced")
    mode = data.get("mode", "auto")
    models = data.get("models", [])
    if type(maximum) is not int or not 1 <= maximum <= 6 or priority not in PRIORITIES or mode not in ("auto", "manual") or not isinstance(models, list):
        raise ValueError("Invalid Delegate settings")
    return {"max_agents": maximum, "priority": priority, "mode": mode, "models": models}


def local_model_catalog(home: Path) -> dict:
    if PLATFORM == "claude":
        return {"source": "known Claude aliases", "candidates": ["haiku", "sonnet", "opus"],
                "live_availability": "unknown from local CLI"}
    for name in ("models_cache.codex_work_desktop.json", "models_cache.json"):
        path = home / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            candidates = [item["slug"] for item in data["models"]
                          if item.get("visibility") == "list" and item.get("supported_in_api")]
            return {"source": str(path), "candidates": candidates,
                    "live_availability": "unknown from local CLI; cache may be stale"}
        except (OSError, ValueError, KeyError, TypeError):
            return {"source": str(path), "error": "Invalid local model cache",
                    "live_availability": "unknown from local CLI"}
    return {"source": None, "candidates": [], "live_availability": "unknown from local CLI"}


def normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def ownership_conflict(first: list[str], second: list[str]) -> bool:
    for left in first:
        for right in second:
            a, b = left.replace("\\", "/").casefold().rstrip("/"), right.replace("\\", "/").casefold().rstrip("/")
            if a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                return True
    return False


def usage_totals(run: dict) -> tuple[int, float]:
    entries = run["assignments"]
    return sum(entry.get("tokens") or 0 for entry in entries), round(sum(entry.get("cost_usd") or 0.0 for entry in entries), 6)


def budget_check(run: dict, estimate_tokens: int | None, estimate_usd: float | None) -> None:
    tokens, cost = usage_totals(run)
    active = [entry for entry in run["assignments"] if entry["status"] == "active"]
    reserved_tokens = sum(entry.get("estimate_tokens") or 0 for entry in active)
    reserved_usd = sum(entry.get("estimate_usd") or 0.0 for entry in active)
    budget = run["budget"]
    if budget["tokens"] is not None:
        if estimate_tokens is None:
            raise ValueError("A token budget requires --estimate-tokens before assignment")
        if tokens + reserved_tokens + estimate_tokens > budget["tokens"]:
            raise ValueError("Estimated assignment exceeds the remaining token budget")
    if budget["usd"] is not None:
        if estimate_usd is None:
            raise ValueError("A USD budget requires --estimate-usd before assignment")
        if cost + reserved_usd + estimate_usd > budget["usd"]:
            raise ValueError("Estimated assignment exceeds the remaining USD budget")
    if any(entry["status"] == "awaiting_usage" for entry in run["assignments"]):
        raise ValueError("Record usage for completed assignments before dispatching under a budget")


def recommendation(run: dict, kind: str, candidates: list[str], directory: Path) -> dict:
    observations: dict[str, list[dict]] = {model: [] for model in candidates}
    for path in directory.glob("*.json"):
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
            if history.get("version") != 1 or not isinstance(history.get("assignments"), list):
                continue
            for entry in history["assignments"]:
                if entry["model"] in observations and entry.get("kind") == kind and entry["status"] == "done" and entry["elapsed_seconds"] is not None:
                    observations[entry["model"]].append(entry)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    ranked = []
    for model, entries in observations.items():
        if not entries:
            continue
        successes = sum(entry["outcome"] == "success" for entry in entries)
        rated = [entry["score"] for entry in entries if entry.get("score") is not None]
        mean_score = round(sum(rated) / len(rated), 2) if rated else None
        mean_seconds = round(sum(entry["elapsed_seconds"] for entry in entries) / len(entries), 2)
        costs = [entry["cost_usd"] for entry in entries if entry.get("cost_usd") is not None]
        mean_cost = round(sum(costs) / len(costs), 6) if costs else None
        ranked.append({"model": model, "samples": len(entries), "successes": successes,
                       "mean_score": mean_score, "mean_seconds": mean_seconds, "mean_cost_usd": mean_cost})
    priority = run["priority"]
    if priority == "speed":
        ranked.sort(key=lambda item: (-item["successes"] / item["samples"], item["mean_seconds"]))
    elif priority == "cost":
        ranked.sort(key=lambda item: (-item["successes"] / item["samples"], item["mean_cost_usd"] if item["mean_cost_usd"] is not None else float("inf")))
    else:
        ranked.sort(key=lambda item: (-item["successes"] / item["samples"], -(item["mean_score"] or 0), item["mean_seconds"]))
    return {"priority": priority, "kind": kind, "observations": ranked, "unobserved": [model for model in candidates if not observations[model]],
            "suggestion": ranked[0]["model"] if ranked else None,
            "note": "Observed run history only; verify current capability, price, and availability before spawning. Small samples are uncertain."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=RUNS)
    parser.add_argument("--settings-home", type=Path, default=HOME)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("objective")
    start.add_argument("--id")
    start.add_argument("--budget-tokens")
    start.add_argument("--budget-usd")
    for name in ("status", "progress", "calls", "pause", "resume", "stop"):
        command = commands.add_parser(name)
        command.add_argument("id")
    commands.add_parser("list")
    commands.add_parser("diagnostics")
    checkpoint = commands.add_parser("checkpoint")
    checkpoint.add_argument("id")
    checkpoint.add_argument("summary")
    assignment = commands.add_parser("assign")
    assignment.add_argument("id")
    assignment.add_argument("agent")
    assignment.add_argument("model")
    assignment.add_argument("purpose")
    assignment.add_argument("--kind", choices=("routine", "general", "complex"), required=True)
    assignment.add_argument("--expected", required=True)
    assignment.add_argument("--accept", required=True)
    assignment.add_argument("--owns", action="append", default=[])
    assignment.add_argument("--retry-of")
    assignment.add_argument("--estimate-tokens")
    assignment.add_argument("--estimate-usd")
    finish = commands.add_parser("finish")
    finish.add_argument("id")
    finish.add_argument("agent")
    finish.add_argument("outcome", choices=OUTCOMES)
    finish.add_argument("summary")
    usage = commands.add_parser("usage")
    usage.add_argument("id")
    usage.add_argument("agent")
    usage.add_argument("tokens")
    usage.add_argument("usd")
    usage.add_argument("--score", type=int, choices=range(1, 6))
    rate = commands.add_parser("rate")
    rate.add_argument("id")
    rate.add_argument("assignment_id")
    rate.add_argument("score", type=int, choices=range(1, 6))
    route = commands.add_parser("recommend")
    route.add_argument("id")
    route.add_argument("kind", choices=("routine", "general", "complex"))
    route.add_argument("models", nargs="+")
    call = commands.add_parser("call")
    call.add_argument("id")
    call.add_argument("tool")
    call.add_argument("target")
    call.add_argument("purpose")
    call.add_argument("outcome")
    args = parser.parse_args()

    if args.command == "diagnostics":
        config = settings(args.settings_home)
        print(json.dumps({"settings": config, "runs_dir": str(args.runs_dir),
                          "saved_runs": len(list(args.runs_dir.glob("*.json"))),
                          "model_catalog": local_model_catalog(args.settings_home),
                          "manual_pool_empty": config["mode"] == "manual" and not config["models"],
                          "host_cli_present": shutil.which(PLATFORM) is not None,
                          "agent_tool_available": "unknown from local CLI",
                          "agent_resume_available": "unknown from local CLI",
                          "usage_meter_available": "unknown from local CLI"}))
        return 0
    if args.command == "list":
        runs = []
        for path in args.runs_dir.glob("*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                if item.get("version") == 1 and IDENTIFIER.fullmatch(item.get("id", "")):
                    runs.append({key: item[key] for key in ("id", "objective", "status", "updated_at")})
            except (OSError, ValueError, KeyError, TypeError):
                continue
        print(json.dumps(sorted(runs, key=lambda item: item["updated_at"], reverse=True)))
        return 0
    if args.command == "start":
        config = settings(args.settings_home)
        identifier = args.id or uuid.uuid4().hex[:12]
        path = run_path(args.runs_dir, identifier)
        if path.exists():
            raise ValueError("Run ID already exists")
        run = {"version": 1, "id": identifier, "objective": args.objective, "status": "active",
               "created_at": now(), "updated_at": now(), "max_agents": config["max_agents"],
               "priority": config["priority"], "routing": {"mode": config["mode"], "models": config["models"]},
               "budget": {"tokens": optional_positive_int(args.budget_tokens),
               "usd": optional_positive_float(args.budget_usd)}, "checkpoint": "", "agents": {}, "assignments": [], "calls": []}
        write_json(path, run)
    else:
        run = read_run(args.runs_dir, args.id)
        path = run_path(args.runs_dir, args.id)
        if args.command == "status":
            tokens, cost = usage_totals(run)
            print(json.dumps({**run, "usage_total": {"tokens": tokens, "usd": cost}}))
            return 0
        if args.command == "progress":
            counts = {status: sum(entry["status"] == status for entry in run["assignments"]) for status in ("active", "awaiting_usage", "done")}
            active = [{"id": entry["id"], "agent": entry["agent"], "model": entry["model"], "purpose": entry["purpose"]}
                      for entry in run["assignments"] if entry["status"] == "active"]
            tokens, cost = usage_totals(run)
            outcomes = {outcome: sum(entry["outcome"] == outcome for entry in run["assignments"]) for outcome in OUTCOMES}
            print(json.dumps({"id": run["id"], "status": run["status"], "objective": run["objective"],
                              "checkpoint": run["checkpoint"], "counts": counts, "outcomes": outcomes, "active": active,
                              "agents_used": len(run["agents"]), "max_agents": run["max_agents"],
                              "usage_total": {"tokens": tokens, "usd": cost}, "budget": run["budget"]}))
            return 0
        if args.command == "calls":
            print(json.dumps(run.get("calls", [])))
            return 0
        if args.command == "recommend":
            print(json.dumps(recommendation(run, args.kind, list(dict.fromkeys(args.models)), args.runs_dir)))
            return 0
        if args.command == "pause":
            if run["status"] != "active":
                raise ValueError("Only an active run can be paused")
            run["status"] = "paused"
        elif args.command == "resume":
            if run["status"] != "paused":
                raise ValueError("Only a paused run can be resumed")
            run["status"] = "active"
        elif args.command == "stop":
            if run["status"] == "stopped":
                raise ValueError("Run is already stopped")
            run["status"] = "stopped"
        elif args.command == "checkpoint":
            if run["status"] == "stopped":
                raise ValueError("Cannot checkpoint a stopped run")
            run["checkpoint"] = args.summary
        elif args.command == "call":
            run.setdefault("calls", []).append({"at": now(), "tool": args.tool, "target": args.target,
                                                  "purpose": args.purpose, "outcome": args.outcome})
        elif args.command == "assign":
            if run["status"] != "active":
                raise ValueError("Run must be active to assign work")
            if run.get("routing", {}).get("mode") == "manual" and args.model not in run["routing"]["models"]:
                raise ValueError("Model is outside this run's saved manual pool")
            if args.agent not in run["agents"] and len(run["agents"]) >= run["max_agents"]:
                raise ValueError("Distinct-agent limit reached; reuse an existing agent")
            if args.agent in run["agents"] and run["agents"][args.agent] != args.model:
                raise ValueError("An existing agent's model cannot change")
            if any(entry["agent"] == args.agent and entry["status"] == "active" for entry in run["assignments"]):
                raise ValueError("Agent already has active work")
            prior = {entry["id"]: entry for entry in run["assignments"]}
            if args.retry_of and (args.retry_of not in prior or prior[args.retry_of]["outcome"] not in ("failed", "blocked")):
                raise ValueError("--retry-of must name a failed or blocked assignment")
            if not args.retry_of and any(normalized(entry["purpose"]) == normalized(args.purpose) for entry in run["assignments"]):
                raise ValueError("Duplicate assignment purpose; use --retry-of for an intentional retry")
            for entry in run["assignments"]:
                if entry["status"] == "active" and ownership_conflict(entry.get("owns", []), args.owns):
                    raise ValueError(f"File ownership overlaps active assignment {entry['id']}")
            estimated_tokens = nonnegative_int(args.estimate_tokens) if args.estimate_tokens is not None else None
            estimated_usd = nonnegative_float(args.estimate_usd) if args.estimate_usd is not None else None
            budget_check(run, estimated_tokens, estimated_usd)
            run["agents"][args.agent] = args.model
            run["assignments"].append({"id": f"A{len(run['assignments']) + 1}", "agent": args.agent,
                                       "model": args.model, "kind": args.kind, "purpose": args.purpose, "expected": args.expected,
                                       "accept": args.accept, "owns": args.owns, "retry_of": args.retry_of,
                                       "estimate_tokens": estimated_tokens, "estimate_usd": estimated_usd,
                                       "status": "active", "dispatched_at": now(), "completed_at": None,
                                       "elapsed_seconds": None, "outcome": None, "summary": None,
                                       "tokens": None, "cost_usd": None, "usage_recorded": False, "score": None})
        elif args.command == "finish":
            matches = [entry for entry in run["assignments"] if entry["agent"] == args.agent and entry["status"] == "active"]
            if not matches:
                raise ValueError("No active assignment for this agent")
            entry = matches[-1]
            entry["completed_at"] = now()
            entry["elapsed_seconds"] = max(0.0, round((datetime.fromisoformat(entry["completed_at"]) - datetime.fromisoformat(entry["dispatched_at"])).total_seconds(), 3))
            entry["outcome"] = args.outcome
            entry["summary"] = args.summary
            entry["status"] = "awaiting_usage" if any(value is not None for value in run["budget"].values()) else "done"
        elif args.command == "usage":
            matches = [entry for entry in run["assignments"] if entry["agent"] == args.agent and entry["completed_at"]
                       and (entry["status"] == "awaiting_usage" or not entry.get("usage_recorded", False))]
            if not matches:
                raise ValueError("No completed assignment awaiting usage for this agent")
            entry = matches[0]
            entry["tokens"] = known_int(args.tokens)
            entry["cost_usd"] = known_float(args.usd)
            entry["usage_recorded"] = True
            if args.score is not None:
                entry["score"] = args.score
            budget = run["budget"]
            missing_required = (budget["tokens"] is not None and entry["tokens"] is None) or (budget["usd"] is not None and entry["cost_usd"] is None)
            entry["status"] = "awaiting_usage" if missing_required else "done"
        elif args.command == "rate":
            matches = [entry for entry in run["assignments"] if entry["id"] == args.assignment_id and entry["completed_at"]]
            if not matches:
                raise ValueError("Assignment does not exist or is unfinished")
            matches[0]["score"] = args.score
        run["updated_at"] = now()
        write_json(path, run)
    print(json.dumps(run))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"delegate run: {exc}", file=sys.stderr)
        raise SystemExit(1)
