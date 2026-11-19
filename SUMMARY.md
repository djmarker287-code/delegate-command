# Summary

Delegate is a reusable orchestration command for Codex and Claude Code. The main chat model stays in charge of planning, routing, integration, and final verification. It chooses a task-sized number of subagents, from zero to a saved maximum of six, and gives each a distinct assignment.

Automatic mode selects worker models by task. Manual mode limits choices to a saved model pool without forcing every model to work. The setting persists across chats on the same machine. The final report names the workers used, their assignments, results, tool calls, and observed elapsed times.

Codex uses `$delegate` or `/prompts:delegate`; Claude Code uses `/delegate`. Each platform has its own local settings file and model catalog. A shared prompt describes the same behavior, but the two products use different subagent tools and model names.

The bottom of [README.md](README.md#copy-and-paste-prompts-to-create-the-skills) has complete copy-and-paste prompts to create the Codex and Claude Code skills from scratch.
