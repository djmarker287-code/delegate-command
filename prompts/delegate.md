---
description: Keep routing task work through up to six reusable agents
argument-hint: auto <1-6> | count <1-6> | select <models...> | goal <objective> | <task>
---

Find the installed `delegate` skill in the user-level Codex skills directory. Read its `SKILL.md` and follow it.

Delegate command input: $ARGUMENTS

Interpret `auto`, `manual`, `count`, `select`, `add`, `remove`, `models`, `status`, `reset`, and `off` as delegate controls. Interpret `goal <objective>` as a goal that uses delegation. If no input is given, activate delegation for this chat and show the setup.

For a task, read the saved settings, then keep the selected main chat model as planner, router, progress tracker, and final reviewer. Build a backlog with dependencies and completion criteria. Give agents distinct substantive assignments. Each time an agent finishes, check its result and give the next ready assignment to an idle agent, using `followup_task` to reuse an existing agent when available. Continue through every batch, including fixes and verification, until the entire task is complete or genuinely blocked. The saved limit caps distinct agents across the task at six, not the number of assignments. Never take over unfinished implementation just because the first batch ended. Do substantive work in the main chat only if the user explicitly asks you to step in or no usable worker is available; explain the exception. If agents cannot be reused after the cap is reached, report that limitation instead of evading the cap.

Record every agent call and each assignment's observed dispatch-to-completion time. Finish with the worker and call report required by the skill. Preserve this routing behavior on later turns in this chat until `off`, including goal continuations.
