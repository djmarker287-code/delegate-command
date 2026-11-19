# Summary

Delegate is a reusable orchestration command for Codex and Claude Code. The main chat model plans, routes, tracks progress, and reviews. Agents perform substantive work across as many successive assignments as the task requires. When a worker finishes, the coordinator checks its result and routes the next ready job instead of taking over the unfinished work. The saved maximum of six limits distinct agents per task, not the number of assignments.

Automatic mode selects worker models by task. Manual mode limits choices to a saved model pool without forcing every model to work. The setting persists across chats on the same machine. Existing agents are reused or resumed for later assignments when supported. The main model steps into substantive work only when asked or no usable worker is available. The final report names the workers used, all assignments, results, tool calls, and observed elapsed times.

Codex uses `$delegate` or `/prompts:delegate`; Claude Code uses `/delegate`. Each platform has its own local settings file and model catalog. A shared prompt describes the same behavior, but the two products use different subagent tools and model names.

The bottom of [README.md](README.md#copy-and-paste-prompts-to-create-the-skills) has complete copy-and-paste prompts to create the Codex and Claude Code skills from scratch.

The local development version adds routing priorities and tracked task checkpoints. It saves a concise progress summary and agent history across chats without saving a full backlog. Each assignment has an expected result, acceptance check, optional file ownership, outcome, and observed elapsed time. The helpers reject a seventh distinct agent, duplicate work, and overlapping active file edits. They track actual usage when available, check per-task budget estimates, suggest models from observed results, and report local diagnostics. The chat model still calls the platform's agent tools and verifies live model availability.
