# `/delegate` prompt for Claude Code

Claude Code loads a skill named `delegate` as a real `/delegate` command. This repository includes that skill at [.claude/skills/delegate/SKILL.md](.claude/skills/delegate/SKILL.md). It uses Claude Code's Agent tool and the model aliases `haiku`, `sonnet`, and `opus`. The main Claude model remains the planner and router, handing out successive assignments until the whole task is done.

## Install

Requires Claude Code with subagents and Python 3.11 or later. For all local Claude Code projects, copy the skill to `~/.claude/skills/delegate/`. From this repository in Windows PowerShell:

```powershell
$claudeHome = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $env:USERPROFILE '.claude' }
New-Item -ItemType Directory -Force (Join-Path $claudeHome 'skills/delegate') | Out-Null
Copy-Item ./.claude/skills/delegate/* (Join-Path $claudeHome 'skills/delegate') -Recurse -Force
```

For one repository, keep `.claude/skills/delegate/` in that repository instead. Start a new Claude Code session and type `/delegate status` to check that it loaded. Claude saves routing settings in `~/.claude/delegate.json` or `CLAUDE_CONFIG_DIR/delegate.json`.

## Commands

```text
/delegate auto 6
/delegate Build a mini game
/delegate select haiku sonnet
/delegate count 2
/delegate manual
/delegate models
/delegate status
/delegate off
/delegate priority speed
/delegate start --budget-tokens 50000 --budget-usd 5 Build a mini game
/delegate runs
/delegate progress <run-id>
/delegate calls <run-id>
/delegate pause <run-id>
/delegate resume <run-id>
/delegate stop <run-id>
/delegate diagnostics
```

`auto 6` means **up to** six distinct workers for a task, including sequential and nested agents. Claude can reuse or resume them for later assignments when supported; the cap does not limit the number of assignments. `select haiku sonnet` saves a manual pool; it does not force both models to work on every task. `manual` returns to that saved pool after using auto mode. `reset` clears the pool and returns to auto mode with a limit of three.

Tracked tasks use `scripts/run.py` to save a concise progress checkpoint and assignment history in the user-level Claude configuration directory. The helper reports active agents, outcomes, calls, elapsed time, and actual usage when available. It rejects duplicate assignments, overlapping active file ownership, and a seventh distinct agent. It cannot operate the Agent tool or meter usage on its own. A budget checks estimates against recorded usage and pauses further dispatch when usage is unavailable; it is not a provider-side spending cap. `diagnostics` reports local checks and marks live capabilities it cannot inspect as unknown.

Before spawning another Agent, check `progress` for an idle existing Agent and resume it when suitable. A new Agent after the first needs a concrete `--new-agent-reason`, such as independent parallel work or a different needed model. Record failed spawns with `run.py spawn-failed` so they do not consume a distinct-agent slot.

The Agent tool can accept a per-call model alias, but account policy and model availability still apply. Claude Code cannot use the GPT model IDs saved by the Codex version unless you separately provide a compatible integration. Claude Code's `/delegate goal <objective>` is a long-task instruction; it does not create Codex's native `/goal` mode.

## Copyable prompt for a Claude conversation

For a Claude conversation where a skill cannot be installed, paste this prompt. Delegation requires the Agent tool or equivalent subagent capability in that conversation:

```text
Act as the coordinator for this task. Keep the model selected for the main conversation as planner, router, and final reviewer. Give substantive work to agents. Keep a working plan with dependencies and completion criteria, and save a concise progress checkpoint without persisting a full backlog. Choose no more than six distinct workers for the task, including sequential and nested agents. Give each a unique assignment, expected output, acceptance check, and separate file ownership when relevant. Choose the best available Claude model for each agent: Haiku for bounded routine work, Sonnet for general work, and Opus when complexity warrants it. As each agent finishes, check its result and give the next ready assignment to an idle agent. Route failed checks back for repair. Before each fresh spawn, check for an idle existing agent and reuse or resume it when suitable. Give a concrete reason for every additional agent when reuse is unsuitable. The limit caps distinct agents, not assignments. Continue through later batches until the task is complete or genuinely blocked; do not take over the remaining implementation after the first batch. Do substantive work directly only if I ask you to step in or no usable worker is available, and explain that exception. If agents cannot be resumed at the cap, report that limitation. Apply my saved speed/cost/quality preference, use observed outcomes as advisory evidence, and verify live model availability. Report each subagent call, assignment, outcome, and observed dispatch-to-completion interval. Record actual token use and cost only when the platform provides them; pause budgeted dispatch if usage needed for accounting is unavailable. Follow the current plan, review, or long-task boundaries. Task: <replace this with your task>
```

Claude Code's [skills documentation](https://code.claude.com/docs/en/skills) describes `/skill-name` invocation. Its [subagent documentation](https://code.claude.com/docs/en/sub-agents) describes the Agent tool and per-invocation model aliases.
