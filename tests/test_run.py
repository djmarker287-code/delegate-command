"""Behavior checks for both local Delegate checkpoint helpers."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [ROOT / "skills/delegate/scripts/run.py", ROOT / ".claude/skills/delegate/scripts/run.py"]
SETTINGS_SCRIPTS = [ROOT / "skills/delegate/scripts/delegate.py", ROOT / ".claude/skills/delegate/scripts/delegate.py"]


def invoke(script: Path, runs: Path, home: Path, *arguments: str, success: bool = True) -> dict | str:
    result = subprocess.run([sys.executable, str(script), "--runs-dir", str(runs), "--settings-home", str(home), *arguments],
                            capture_output=True, text=True)
    if success:
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    assert result.returncode != 0, result.stdout
    return result.stderr


class RunTests(unittest.TestCase):
    def test_priority_migrates_without_losing_settings(self):
        for script in SETTINGS_SCRIPTS:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as temporary:
                state = Path(temporary) / "delegate.json"
                old_version = 2 if "skills/delegate/scripts" in script.as_posix() and ".claude" not in script.as_posix() else 1
                state.write_text(json.dumps({"version": old_version, "mode": "auto", "models": [], "max_agents": 4}), encoding="utf-8")
                result = subprocess.run([sys.executable, str(script), "priority", "cost", "--state", str(state)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                updated = json.loads(state.read_text(encoding="utf-8"))
                self.assertEqual(updated["priority"], "cost")
                self.assertEqual(updated["max_agents"], 4)
                self.assertEqual(updated["mode"], "auto")

    def test_agent_cap_reuse_duplicate_overlap_and_progress(self):
        for script in SCRIPTS:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                home, runs = root / "home", root / "runs"
                home.mkdir()
                (home / "delegate.json").write_text(json.dumps({"mode": "auto", "models": [], "max_agents": 6,
                                                                 "priority": "speed"}), encoding="utf-8")
                run = invoke(script, runs, home, "start", "Build a game", "--id", "game")
                self.assertEqual(run["max_agents"], 6)
                for index in range(6):
                    invoke(script, runs, home, "assign", "game", f"agent{index}", "model-a", f"piece {index}",
                           "--kind", "general", "--expected", "Working code", "--accept", "Checks pass",
                           "--owns", f"src/part{index}")
                self.assertIn("Distinct-agent limit", invoke(script, runs, home, "assign", "game", "agent6", "model-a", "extra",
                                                                "--kind", "general", "--expected", "Code", "--accept", "Works", success=False))
                invoke(script, runs, home, "finish", "game", "agent0", "success", "Delivered")
                self.assertIn("Duplicate assignment", invoke(script, runs, home, "assign", "game", "agent0", "model-a", "piece 0",
                                                                "--kind", "general", "--expected", "Code", "--accept", "Works", success=False))
                self.assertIn("overlaps", invoke(script, runs, home, "assign", "game", "agent0", "model-a", "new work",
                                                   "--kind", "general", "--expected", "Code", "--accept", "Works",
                                                   "--owns", "src/part1/sub", success=False))
                invoke(script, runs, home, "assign", "game", "agent0", "model-a", "next piece",
                       "--kind", "general", "--expected", "Code", "--accept", "Works")
                progress = invoke(script, runs, home, "progress", "game")
                self.assertEqual(progress["agents_used"], 6)
                self.assertEqual(progress["counts"]["active"], 6)
                self.assertEqual(len(progress["active"]), 6)
                self.assertIn("Run must be active", self._pause_and_try_assign(script, runs, home))
                invoke(script, runs, home, "resume", "game")
                invoke(script, runs, home, "call", "game", "followup_task", "agent0", "next piece", "dispatched")
                self.assertEqual(len(invoke(script, runs, home, "calls", "game")), 1)
                invoke(script, runs, home, "checkpoint", "game", "Six agents active; next review after results")
                self.assertIn("Six agents active", invoke(script, runs, home, "status", "game")["checkpoint"])
                invoke(script, runs, home, "stop", "game")
                self.assertIn("Run must be active", invoke(script, runs, home, "assign", "game", "agent0", "model-a", "after stop",
                                                           "--kind", "routine", "--expected", "Code", "--accept", "Works", success=False))

    def _pause_and_try_assign(self, script: Path, runs: Path, home: Path) -> str:
        invoke(script, runs, home, "pause", "game")
        return invoke(script, runs, home, "assign", "game", "agent0", "model-a", "paused work",
                      "--kind", "routine", "--expected", "Code", "--accept", "Works", success=False)

    def test_budget_usage_retry_and_observed_recommendation(self):
        for script in SCRIPTS:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                home, runs = root / "home", root / "runs"
                home.mkdir()
                invoke(script, runs, home, "start", "Review migration", "--id", "review",
                       "--budget-tokens", "100", "--budget-usd", "1")
                invoke(script, runs, home, "assign", "review", "agent1", "model-a", "review module",
                       "--kind", "complex", "--expected", "Findings", "--accept", "Evidence for each finding",
                       "--estimate-tokens", "50", "--estimate-usd", "0.5")
                self.assertIn("exceeds", invoke(script, runs, home, "assign", "review", "agent2", "model-b", "review tests",
                                                 "--kind", "complex", "--expected", "Findings", "--accept", "Evidence",
                                                 "--estimate-tokens", "60", "--estimate-usd", "0.6", success=False))
                invoke(script, runs, home, "finish", "review", "agent1", "failed", "Check failed")
                self.assertIn("Record usage", invoke(script, runs, home, "assign", "review", "agent1", "model-a", "review module",
                                                       "--kind", "complex", "--expected", "Fix", "--accept", "Passes",
                                                       "--retry-of", "A1", "--estimate-tokens", "40", "--estimate-usd", "0.4", success=False))
                invoke(script, runs, home, "usage", "review", "agent1", "40", "0.4", "--score", "2")
                invoke(script, runs, home, "assign", "review", "agent1", "model-a", "review module",
                       "--kind", "complex", "--expected", "Fix", "--accept", "Passes", "--retry-of", "A1",
                       "--estimate-tokens", "40", "--estimate-usd", "0.4")
                invoke(script, runs, home, "finish", "review", "agent1", "success", "Fixed")
                invoke(script, runs, home, "usage", "review", "agent1", "35", "0.3", "--score", "5")
                observed = invoke(script, runs, home, "recommend", "review", "complex", "model-a", "model-b")
                self.assertEqual(observed["suggestion"], "model-a")
                self.assertEqual(observed["unobserved"], ["model-b"])
                invoke(script, runs, home, "start", "Second task", "--id", "second")
                learned = invoke(script, runs, home, "recommend", "second", "complex", "model-a", "model-b")
                self.assertEqual(learned["suggestion"], "model-a")
                progress = invoke(script, runs, home, "progress", "review")
                self.assertEqual(progress["usage_total"]["tokens"], 75)
                self.assertEqual(progress["outcomes"]["success"], 1)
                self.assertEqual(progress["outcomes"]["failed"], 1)
                self.assertIn("review", [item["id"] for item in invoke(script, runs, home, "list")])
                diagnostics = invoke(script, runs, home, "diagnostics")
                self.assertEqual(diagnostics["agent_tool_available"], "unknown from local CLI")
                self.assertEqual(diagnostics["model_catalog"]["live_availability"].split(";")[0], "unknown from local CLI")

    def test_manual_pool_and_partial_usage(self):
        for script in SCRIPTS:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                home, runs = root / "home", root / "runs"
                home.mkdir()
                (home / "delegate.json").write_text(json.dumps({"mode": "manual", "models": ["model-a"],
                                                                 "max_agents": 2, "priority": "quality"}), encoding="utf-8")
                invoke(script, runs, home, "start", "Test partial metering", "--id", "partial", "--budget-tokens", "100")
                self.assertIn("manual pool", invoke(script, runs, home, "assign", "partial", "agent1", "model-b", "first",
                                                      "--kind", "routine", "--expected", "Result", "--accept", "Correct",
                                                      "--estimate-tokens", "50", success=False))
                invoke(script, runs, home, "assign", "partial", "agent1", "model-a", "first",
                       "--kind", "routine", "--expected", "Result", "--accept", "Correct", "--estimate-tokens", "50")
                invoke(script, runs, home, "finish", "partial", "agent1", "success", "Done")
                invoke(script, runs, home, "usage", "partial", "agent1", "30", "unknown")
                self.assertEqual(invoke(script, runs, home, "status", "partial")["assignments"][0]["status"], "done")
                invoke(script, runs, home, "assign", "partial", "agent1", "model-a", "second",
                       "--kind", "routine", "--expected", "Result", "--accept", "Correct", "--estimate-tokens", "50")
                invoke(script, runs, home, "finish", "partial", "agent1", "success", "Done")
                invoke(script, runs, home, "usage", "partial", "agent1", "unknown", "0.1")
                self.assertEqual(invoke(script, runs, home, "status", "partial")["assignments"][1]["status"], "awaiting_usage")
                self.assertIn("Record usage", invoke(script, runs, home, "assign", "partial", "agent1", "model-a", "third",
                                                       "--kind", "routine", "--expected", "Result", "--accept", "Correct",
                                                       "--estimate-tokens", "20", success=False))


if __name__ == "__main__":
    unittest.main()
