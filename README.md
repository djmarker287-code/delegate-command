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

## Copy-and-paste prompts to create the skills

These prompts create the skills from scratch on your own machine. Paste the Codex prompt into Codex or the Claude prompt into Claude Code. Each prompt includes the behavior, files, commands, persistence, and checks; the repository is not required.

### Codex / ChatGPT Work creation prompt

````text
Create and install a personal Codex skill named `delegate` that routes work to subagents. Do the implementation now; do not merely explain it or stop after writing a plan. Use Python 3.11+ standard library for the settings helper. Preserve existing Codex config and unrelated files.

Create these files under CODEX_HOME (default ~/.codex):
1. skills/delegate/SKILL.md with YAML name and description.
2. skills/delegate/scripts/delegate.py for persistent settings.
3. skills/delegate/agents/openai.yaml with a display name, short description, and a default prompt mentioning `$delegate`.
4. prompts/delegate.md, a Codex custom prompt with a description, argument hint, and `$ARGUMENTS` that loads the installed delegate skill. This provides `/prompts:delegate` in the CLI. Tell me plainly that Codex cannot register a native bare `/delegate` through a custom prompt; `$delegate` invokes the skill in supported chat surfaces.

The main chat's currently selected model is always the planner, router, integrator, and final reviewer. Do not change that model when using Delegate. Store settings across chats in CODEX_HOME/delegate.json, never in the project. Use a JSON object with version, mode (`auto` or `manual`), models (a manual model ID list), and max_agents (an integer from 1 through 6). Default to auto mode and max_agents 3. Read and validate settings every delegated task. Read available worker model IDs from a Codex model cache or `codex debug models`; reject unavailable manual model IDs without changing saved settings. Write updates atomically.

Implement these subcommands: `auto [1-6]` and `select auto [1-6]` to enable automatic model choice; `count <1-6>` to change only the limit; `select <model...>` to replace the manual pool; `add <model...>` and `remove <model...>` to edit it; `manual` to restore that pool; `models`, `status`, and `reset` for inspection and reset; `off` to stop delegation only in the current chat; `goal <objective>` to run a Codex goal with the routing rule in its persisted objective; and any other text as a task. Let a normal `/goal` after activation retain delegation behavior. Respect Plan mode and review boundaries.

For each task, the main model chooses the fewest useful workers, including zero when delegation overhead exceeds the benefit. The saved limit is a ceiling on total distinct agents spawned for that task, including sequential spawns and descendants, not a target; never exceed six or the platform's lower limit. In auto mode, select the best available model separately for each assignment by capability, latency, and cost. In manual mode, use only a useful subset of the saved pool; never force every saved model to run. Give workers distinct, concrete assignments and file ownership where relevant. Do not duplicate work to fill the limit. Pass the selected model explicitly to each spawn when supported, and report an unavailable model instead of silently substituting. The main model checks and integrates results.

Log each subagent call with target, model, distinct assignment or purpose, and outcome. Capture dispatch and observed completion times. In the final answer, include a concise worker table and call list; label timing as dispatch-to-completion elapsed time unless the platform supplies actual active runtime. If no workers were used, say why. Do not claim cost savings without usage evidence.

Validate the skill and test the settings helper with temporary state files: auto/manual switching, preserving a manual pool, a six-agent maximum, rejecting 0 and 7, rejecting an unavailable model without mutation, and reset. Report the installed paths and exact invocation syntax.
````

### Claude Code creation prompt

````text
Create and install a personal Claude Code skill named `delegate` that becomes the `/delegate` command. Do the implementation now; do not merely explain it or stop after writing a plan. Use Python 3.11+ standard library for the settings helper. Preserve existing Claude settings and unrelated files.

Create ~/.claude/skills/delegate/SKILL.md and ~/.claude/skills/delegate/scripts/delegate.py, or use CLAUDE_CONFIG_DIR instead of ~/.claude when it is set. The skill frontmatter must include `name: delegate`, a concise description, an argument hint, and `disable-model-invocation: true`. Use `$ARGUMENTS` to receive text after `/delegate`. Resolve the helper relative to the skill directory using Claude Code's `${CLAUDE_SKILL_DIR}` substitution. Do not place this command in a Codex directory.

The Claude model selected for the main conversation remains the planner, router, integrator, and final reviewer. Workers are Claude Code subagents launched with the Agent tool. Save settings across local chats in the Claude configuration directory as delegate.json with version, mode (`auto` or `manual`), models, and max_agents (1 through 6). Default to auto mode and max_agents 3. Use Claude's model aliases `haiku`, `sonnet`, and `opus` for the manual pool; verify actual session availability at spawn time. Write settings atomically. Do not claim that Codex GPT model IDs work as Claude subagents without a separate provider integration.

Implement `/delegate auto [1-6]`, `/delegate select auto [1-6]`, `/delegate count <1-6>`, `/delegate select <haiku|sonnet|opus...>`, `/delegate add <models...>`, `/delegate remove <models...>`, `/delegate manual`, `/delegate models`, `/delegate status`, `/delegate reset`, and `/delegate off`. Treat any other argument as the task. Treat `/delegate goal <objective>` as a long-running task instruction with delegation; do not claim it creates Codex's native `/goal` mode.

For each task, use the fewest useful workers, including zero when direct work is faster or cheaper. Never spawn more than the saved maximum, six total, or the platform's lower limit; count sequential and nested workers too. In auto mode, choose Haiku for bounded routine work, Sonnet for general work, and Opus when complexity warrants it, subject to availability and the task's quality needs. In manual mode, choose a useful subset of saved aliases. Pass the alias in the Agent tool's per-invocation model parameter when available. Give every worker a distinct assignment; do not invent or duplicate work to fill the limit. Keep routing and final verification in the main conversation. Respect plan and review boundaries.

Record each Agent and subagent message call, target, model, purpose, outcome, dispatch time, and observed completion time. End with a concise worker table and call list. Label wall time as dispatch-to-completion elapsed time unless actual active runtime is supplied. Do not invent timing or claim savings without usage evidence.

Test the helper using temporary files: auto/manual switching, preserving the manual pool, rejecting 0 and 7, rejecting invalid model aliases without mutation, and reset. Verify Claude Code recognizes `/delegate` if authentication is available; if a live check is blocked, report the exact blocker. Report the installed paths and an example invocation.
````
