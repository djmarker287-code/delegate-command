# Delegate for Codex and Claude Code

Delegate keeps the model selected for the main chat as the planner, router, and final reviewer. It can assign distinct parts of a task to subagents, choosing their models automatically or from a saved manual pool. The saved agent limit is a ceiling from 1 to 6, not a target. Simple tasks can use no subagents.

The coordinator reports each worker's assignment and observed dispatch-to-completion time, plus the subagent calls it used. It works alongside Codex goals, plans, and reviews. See [SUMMARY.md](SUMMARY.md) for the short specification and [PROMPT.md](PROMPT.md) for a standalone prompt.

## Codex setup

Requires Python 3.11 or later and a Codex session with subagent tools. Copy the skill and optional custom prompt into your user-level Codex home (`~/.codex`, or `CODEX_HOME` when set). On Windows PowerShell, from this repository:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
New-Item -ItemType Directory -Force (Join-Path $codexHome 'skills/delegate'), (Join-Path $codexHome 'prompts') | Out-Null
Copy-Item ./skills/delegate/* (Join-Path $codexHome 'skills/delegate') -Recurse -Force
Copy-Item ./prompts/delegate.md (Join-Path $codexHome 'prompts/delegate.md') -Force
```

Open a new Codex or supported ChatGPT Work chat after installation. Invoke the skill with `$delegate` in the composer when that surface exposes local skills and subagent tools. The Codex CLI custom prompt is `/prompts:delegate`. Codex does not register a native bare `/delegate` slash command from a custom prompt; a skill named Delegate may also appear in the app's slash menu. A chat without subagent tools can use [PROMPT.md](PROMPT.md) as guidance but cannot create worker agents.

```text
$delegate auto 6
$delegate Build a mini game
$delegate status
$delegate select gpt-6.2-sol gpt-6-luna
$delegate manual
$delegate goal Finish the migration and verify all tests
```

`auto 6` lets the coordinator choose any available worker model and spawn up to six total agents for a task. `select ...` saves a manual model pool; the coordinator still chooses only the workers useful for each task. `count 2` changes the limit without changing the mode. `add`, `remove`, `models`, `off`, and `reset` are also supported. Settings are saved in the user-level `delegate.json`, outside this repository. `reset` returns to auto mode with a limit of three.

The selected chat model never changes. The coordinator respects the platform's actual concurrency limit and may use fewer than the saved maximum. Agent creation has latency and usage cost, so more agents are not inherently faster or cheaper. Model selection considers task difficulty and current model capabilities; verify actual usage before claiming savings.

## Claude Code

Claude Code has its own `/delegate` skill in [.claude/skills/delegate](.claude/skills/delegate). Follow [README-CLAUDE.md](README-CLAUDE.md) for installation and a Claude-specific prompt. Claude Code subagents use Claude model aliases such as `haiku`, `sonnet`, and `opus`. OpenAI model IDs in Codex's saved pool do not automatically work inside Claude Code.

## Repository layout

- `skills/delegate/`: Codex skill and settings script.
- `prompts/delegate.md`: Codex CLI custom prompt.
- `.claude/skills/delegate/`: Claude Code `/delegate` skill and settings script.
- `PROMPT.md`: Standalone copyable orchestration prompt.
- `README-CLAUDE.md`: Claude Code setup and usage.

No account tokens, model cache, or user settings are included.
