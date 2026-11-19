---
description: Keep routing task work through up to six reusable agents
argument-hint: auto <1-6> | priority <mode> | start <task> | progress | pause | resume | <task>
---

Find the installed `delegate` skill in the user-level Codex skills directory. Read its `SKILL.md` and follow it.

Delegate command input: $ARGUMENTS

Interpret `auto`, `manual`, `count`, `select`, `add`, `remove`, `models`, `status`, `priority`, `reset`, and `off` as delegate controls. Interpret `runs`, `progress`, `calls`, `pause`, `resume`, `stop`, and `diagnostics` as tracked-run controls. Interpret `start [--budget-tokens N] [--budget-usd N] <task>` as a tracked task with optional budget. Interpret `goal <objective>` as a goal that uses delegation. If no input is given, activate delegation for this chat and show the setup.

For a task, read the saved settings and use the skill's `run.py` checkpoint helper. Keep the selected main chat model as planner, router, progress tracker, and final reviewer. Give agents distinct substantive assignments with expected outputs, acceptance checks, and separate file ownership. Each time an agent finishes, check its result and give the next ready assignment to an idle agent, using `followup_task` to reuse an existing agent when available. Route failed checks back to an agent. Continue through every batch until the entire task is complete or genuinely blocked. The saved limit caps distinct agents across the task at six, not the number of assignments. Never take over unfinished implementation just because the first batch ended. Do substantive work in the main chat only if the user explicitly asks you to step in or no usable worker is available; explain the exception. If agents cannot be reused after the cap is reached, report that limitation instead of evading the cap.

Save concise progress checkpoints across turns and chats without storing a full backlog. Record every agent call, each assignment's observed dispatch-to-completion time, and actual usage when available. Use the saved routing preference and observed results as advisory signals; verify current model availability and use a clear fallback within the allowed pool. Respect per-task budget estimates and stop budgeted dispatch when actual usage is unavailable. Finish with the worker and call report required by the skill. Preserve this routing behavior on later turns in this chat until `off`, including goal continuations.
