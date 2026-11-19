# `/delegate` prompt for Claude Code

Claude Code loads a skill named `delegate` as a real `/delegate` command. This repository includes that skill at [.claude/skills/delegate/SKILL.md](.claude/skills/delegate/SKILL.md). It uses Claude Code's Agent tool and the model aliases `haiku`, `sonnet`, and `opus`. The main Claude model remains the planner and router.

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
```

`auto 6` means **up to** six total workers for a task, including sequential and nested agents. Claude chooses fewer when that gives a better result for time, cost, and quality. `select haiku sonnet` saves a manual pool; it does not force both models to work on every task. `manual` returns to that saved pool after using auto mode. `reset` clears the pool and returns to auto mode with a limit of three.

The Agent tool can accept a per-call model alias, but account policy and model availability still apply. Claude Code cannot use the GPT model IDs saved by the Codex version unless you separately provide a compatible integration. Claude Code's `/delegate goal <objective>` is a long-task instruction; it does not create Codex's native `/goal` mode.

## Copyable prompt for a Claude conversation

For a Claude conversation where a skill cannot be installed, paste this prompt. Delegation requires the Agent tool or equivalent subagent capability in that conversation:

```text
Act as the coordinator for this task. Keep the model selected for the main conversation as planner, router, integrator, and final reviewer. If subagents are available, choose the fewest useful workers, no more than six total for the task. Assign each worker a distinct piece of work and choose the best available Claude model for that assignment: Haiku for bounded routine work, Sonnet for general work, and Opus when complexity warrants it. Use no workers when coordination overhead outweighs the benefit. Do not duplicate work to fill the limit. Check and integrate the workers' results yourself. Report each subagent call, its model, distinct assignment, outcome, and observed dispatch-to-completion elapsed time; do not label that as model compute time. Follow the current plan, review, or long-task boundaries. Task: <replace this with your task>
```

Claude Code's [skills documentation](https://code.claude.com/docs/en/skills) describes `/skill-name` invocation. Its [subagent documentation](https://code.claude.com/docs/en/sub-agents) describes the Agent tool and per-invocation model aliases.
