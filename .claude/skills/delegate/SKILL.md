---
name: delegate
description: Route a task to the fewest useful Claude Code subagents, using automatic model choice or a saved manual pool and a six-agent ceiling.
argument-hint: auto <1-6> | select <haiku|sonnet|opus...> | <task>
disable-model-invocation: true
---

# Delegate for Claude Code

Command input: $ARGUMENTS

The Claude model selected for this main conversation is the planner, router, integrator, and final reviewer. Use the Agent tool for workers. Keep this main model unchanged. Run `python "${CLAUDE_SKILL_DIR}/scripts/delegate.py" status` to read saved settings from the user's Claude configuration directory. Use the same script for `models`, `auto <1-6>`, `count <1-6>`, `select <model...>`, `add <model...>`, `remove <model...>`, `manual`, and `reset`. `off` stops delegation in this conversation without clearing saved settings.

For `auto`, choose each worker from the Claude model aliases actually available to this session: `haiku` for bounded routine work, `sonnet` for general tasks, and `opus` when complexity warrants it. In manual mode, choose only from the saved pool. Pass the chosen alias as the Agent tool's per-invocation `model` parameter when supported. If an account policy or tool prevents it, report the actual model or failure instead of claiming the requested one ran. Claude Code does not natively run Codex's GPT worker models through this skill.

For a task, use the fewest useful workers, including zero when direct work is faster or cheaper. The saved `max_agents` limits the total distinct workers spawned for this task, including sequential and nested workers; six is the hard ceiling and platform limits can be lower. Give workers distinct, concrete assignments and separate file ownership when relevant. Do not duplicate tasks or spawn workers just to fill the limit. Keep planning, routing, integration, and verification in the main conversation. Do not authorize descendants unless they fit within the total limit.

Record each Agent, SendMessage, or other subagent call with target, model, purpose, and outcome. Capture clock time before dispatch and when completion is observed. Report dispatch-to-completion elapsed time unless actual active runtime is available. End each delegated task with a concise worker table and call list. If no workers were used, state why. Respect the current conversation's plan or review boundaries. For `goal <objective>`, treat the objective as a long task with this routing rule; Claude Code does not acquire Codex's native `/goal` lifecycle from this skill.
