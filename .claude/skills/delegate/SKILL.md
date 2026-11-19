---
name: delegate
description: Route a task to the fewest useful Claude Code subagents, using automatic model choice or a saved manual pool and a six-agent ceiling.
argument-hint: auto <1-6> | select <haiku|sonnet|opus...> | <task>
disable-model-invocation: true
---

# Delegate for Claude Code

Command input: $ARGUMENTS

The Claude model selected for this main conversation is the planner, router, coordinator, and final reviewer. Use the Agent tool for substantive work and keep this main model unchanged. Run `python "${CLAUDE_SKILL_DIR}/scripts/delegate.py" status` to read saved settings from the user's Claude configuration directory. Use the same script for `models`, `auto <1-6>`, `count <1-6>`, `select <model...>`, `add <model...>`, `remove <model...>`, `manual`, and `reset`. `off` stops delegation in this conversation without clearing saved settings.

For `auto`, choose each worker from the Claude model aliases actually available to this session: `haiku` for bounded routine work, `sonnet` for general tasks, and `opus` when complexity warrants it. In manual mode, choose only from the saved pool. Pass the chosen alias as the Agent tool's per-invocation `model` parameter when supported. If an account policy or tool prevents it, report the actual model or failure instead of claiming the requested one ran. Claude Code does not natively run Codex's GPT worker models through this skill.

For an activated task, keep substantive research, implementation, and routine fixes with workers. The main conversation plans, routes, tracks dependencies, verifies, and reports; it does not take over unfinished work after the first agents return. The main model implements directly only when the user asks it to step in or no usable worker is available; explain that exception. The saved `max_agents` limits the total distinct workers spawned for this task, including sequential and nested workers; six is the hard ceiling and platform limits can be lower. Reuse or resume an existing Agent for later distinct assignments when the tool supports it. The cap limits distinct workers, not assignments or follow-up calls. If the cap is reached and the tool cannot resume workers, report the limitation instead of evading the cap or silently doing the remaining implementation in the main conversation. Give workers distinct, concrete assignments and separate file ownership when relevant. Do not duplicate tasks or spawn workers just to fill the limit. Do not authorize descendants unless they fit within the total limit.

Maintain a backlog with dependencies and completion criteria. Dispatch a useful first batch. As each worker completes, inspect its result, update the backlog, and assign the next ready item to an idle worker. Continue through later batches, fixes, and verification work until the user task is complete or genuinely blocked. Do not stop after the first batch just because those agents finished. Keep main-chat work to coordination, light integration, verification, and the final answer.

Record each Agent, SendMessage, resume, or other subagent call with target, model, purpose, and outcome. Capture clock time before each assignment and when completion is observed. Report dispatch-to-completion elapsed time per work interval unless actual active runtime is available. End each delegated task with a concise worker table covering all batches and a call list. If no worker was available, state why. Respect the current conversation's plan or review boundaries. For `goal <objective>`, keep this backlog and routing rule through the whole long task; Claude Code does not acquire Codex's native `/goal` lifecycle from this skill.
