---
name: delegate
description: Let the chat model plan and route work to a task-sized number of subagents, using saved manual models or automatic model selection, including in goals.
---

# Delegate

The model selected for the current chat is the planner, router, and final decision maker. Workers do distinct assigned work and return evidence. The coordinator integrates and verifies it. Routing settings persist across chats in the user-level Codex home as `delegate.json` (`~/.codex/delegate.json` by default).

Run `python <installed delegate skill directory>/scripts/delegate.py <command>` to manage settings. Resolve the script path from this `SKILL.md` location. `status` reports `mode`, `models`, and `max_agents`; `models` lists catalog candidates. Report the coordinator's model only when reliable session context provides it. Never infer it from user-level config because the chat can override that config.

## Invocation

- `delegate auto <number>` or `delegate select auto <number>`: Save automatic model selection with a maximum of that many agents per task. The number must be 1–6. Omit the number to keep the current limit.
- `delegate count <number>`: Change the per-task agent limit to a number from 1–6 without changing the mode.
- `delegate select <model> [<model> ...]`: Save a manual worker model pool. The chat model stays the coordinator; the planner chooses a subset of that pool per task.
- `delegate manual`: Switch back to the saved manual pool without re-entering its model IDs.
- `delegate add <model> [<model> ...]` or `delegate remove <model> [<model> ...]`: Edit the manual pool.
- `delegate models`, `delegate status`, `delegate reset`: List candidates, show the setup, or reset to auto mode with a limit of three.
- `delegate` without a task: Activate delegation for this chat and show the setup.
- `delegate off`: Stop delegating in this chat while retaining the saved army for future use.
- `delegate <task>`: Activate delegation and carry out the task. Auto mode picks worker models from the available catalog. Manual mode picks only from the saved pool; if that pool is empty, ask the user to select a model or switch to auto.
- `delegate goal <objective>`: If no goal is active, use the available goal command or tool to create the goal. Add this concise condition to its objective: "On every continuation, use the delegate skill; re-read the user-level Codex delegate.json; keep the chat model as coordinator; choose the fewest useful workers up to the saved maximum of six; give each distinct work; record subagent calls and elapsed times for the final report." If a goal is already active, do not replace its objective; treat this command as steering that goal unless the user explicitly asks to replace it. The goal's completion audit, budget, and lifecycle still govern the work.

After activation, use delegation on later tasks in this chat until the user turns it off. Read `status` at the start of each task, including goal continuation turns, so changes from other chats take effect. A normal `/goal` started after delegation is active should continue with this routing behavior; `delegate goal` also writes the routing condition into the goal objective so it survives compaction. In Plan mode, delegate only planning or research and preserve the no-implementation boundary. In review workflows, delegate independent inspections and let the coordinator synthesize the findings. Other workflows keep their own requirements.

For each task, first decide whether delegation will improve total speed, cost, or quality after accounting for spawn and coordination overhead. Use the fewest useful agents, including zero for a task better handled directly. The saved `max_agents` is a ceiling on the **total distinct agents spawned for one task**, including descendants and sequential spawns, never a target; six is the hard maximum. Also obey the platform's concurrency limit. In auto mode, pick the best available model separately for each assignment from the current catalog. In manual mode, choose a subset of the saved pool and reuse a model for different assignments if that is best. Prefer a faster, lower-cost model for bounded routine work and a stronger model when task complexity or error cost warrants it; consult current model capability and price information when needed, and do not promise savings without usage evidence.

Make an assignment ledger only for agents actually used, with a unique task, expected output, and file ownership where relevant. Do not assign the same investigation, implementation, or review to multiple workers or invent work to fill the limit. Pass the chosen model explicitly to each spawn. If model override requires a context-free fork, provide full task context. Keep routing at the coordinator; workers should not spawn descendants unless the coordinator explicitly budgets them within the six-agent total. If a model cannot be spawned, report the failure and do not silently substitute another. Workers may edit separate files; the coordinator resolves shared changes and verifies the final result. Honor user instructions, tool permissions, and workflow boundaries.

## Call and time report

For each subagent call, record its tool name (`spawn_agent`, `followup_task`, `send_message`, `wait_agent`, or `interrupt_agent`), target agent, chosen model when applicable, unique assignment or message purpose, and outcome. Capture the current clock time immediately before a worker is spawned or given a follow-up task and when its completion is observed. Calculate elapsed wall time for each work interval. If the platform provides actual active runtime, report that separately; otherwise label the measurement **dispatch-to-completion elapsed time**, which can include queueing and waiting. Do not invent missing times.

At the end of every delegated task, include a concise table with each used worker's model, distinct assignment, result, and elapsed time, followed by a list of subagent calls with their targets and outcomes. If no agents were needed, say so briefly. For a goal, keep this ledger through continuation turns and include it in the final goal report. The coordinator remains responsible for the final answer and verification.
