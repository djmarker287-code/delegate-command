# Delegate for Codex and Claude Code

Delegate keeps the model selected for the main chat as the planner, router, and final reviewer. Agents do the substantive work across successive batches. As each assignment finishes, the coordinator checks it and routes the next ready job; it does not take over the rest of a long task. The saved limit is a ceiling of 1 to 6 distinct agents per task, not a cap on the number of assignments. Reuse or resume those agents when supported.

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

`auto 6` lets the coordinator choose any available worker model and spawn up to six distinct agents for a task. Those agents can receive many follow-up assignments as the backlog progresses. `select ...` saves a manual model pool; the coordinator still chooses only the workers useful for each task. `count 2` changes the limit without changing the mode. `add`, `remove`, `models`, `off`, and `reset` are also supported. Settings are saved in the user-level `delegate.json`, outside this repository. `reset` returns to auto mode with a limit of three.

The selected chat model never changes. The coordinator respects the platform's actual concurrency limit and may use fewer than the saved maximum. Agent creation has latency and usage cost, so more agents are not inherently faster or cheaper. Model selection considers task difficulty and current model capabilities; verify actual usage before claiming savings.

### Local task checkpoints

Delegate adds `priority balanced|speed|cost|quality` to the settings helper and `skills/delegate/scripts/run.py` for tracked tasks. The helper stores a short progress checkpoint and agent history in the user-level `delegate-runs` directory. It does not persist a full task backlog or call agent tools itself. The coordinator still plans and dispatches work through the session's subagent tools.

```text
$delegate priority cost
$delegate start --budget-tokens 50000 --budget-usd 5 Build a mini game
$delegate runs
$delegate progress <run-id>
$delegate calls <run-id>
$delegate pause <run-id>
$delegate resume <run-id>
$delegate stop <run-id>
$delegate diagnostics
```

Each assignment has an expected output, acceptance check, optional file ownership, and an observed dispatch-to-completion interval. The helper rejects a seventh distinct agent, duplicate assignment, and overlapping active file ownership. It records repairs, call history, actual usage when available, and advisory model observations. Budgets check estimates against recorded usage; they cannot guarantee a provider-side spending cap, so the coordinator pauses budgeted dispatch if usage is unavailable.

`progress` shows idle agents. The coordinator reuses a suitable idle agent before spawning another, and waits for a busy agent when a new spawn would add more overhead than value. After the first agent, `run.py assign` requires `--new-agent-reason` for each fresh agent. A failed spawn can be recorded with `run.py spawn-failed`, which releases its reserved agent slot.

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
5. skills/delegate/scripts/run.py for local task checkpoints, agent and call history, progress, budgets, and diagnostics.

The main chat's currently selected model is always the planner, router, integrator, and final reviewer. Do not change that model when using Delegate. Store settings across chats in CODEX_HOME/delegate.json, never in the project. Use a JSON object with version, mode (`auto` or `manual`), models (a manual model ID list), and max_agents (an integer from 1 through 6). Default to auto mode and max_agents 3. Read and validate settings every delegated task. Read available worker model IDs from a Codex model cache or `codex debug models`; reject unavailable manual model IDs without changing saved settings. Write updates atomically.

Implement these subcommands: `auto [1-6]` and `select auto [1-6]` to enable automatic model choice; `count <1-6>` to change only the limit; `select <model...>` to replace the manual pool; `add <model...>` and `remove <model...>` to edit it; `manual` to restore that pool; `models`, `status`, and `reset` for inspection and reset; `off` to stop delegation only in the current chat; `goal <objective>` to run a Codex goal with the continuous agent-routing rule in its persisted objective; and any other text as a task. Let a normal `/goal` after activation retain delegation behavior across continuation turns. Respect Plan mode and review boundaries.

For each activated task, the main model plans and maintains a backlog with dependencies and completion criteria. Agents do the substantive research, implementation, routine fixes, and verification work. Dispatch a useful first batch, then inspect each result and give the next ready assignment to an idle agent. Keep routing through later batches until the whole task is complete or genuinely blocked; do not stop after the first batch and finish the remaining work in the main chat. Reuse or resume agents where supported. The saved limit is a ceiling on total distinct agents spawned for that task, including sequential spawns and descendants, not a cap on assignments; never exceed six or the platform's lower limit. If agents cannot be resumed at the cap, report the limitation instead of evading it. In auto mode, select the best available model for each agent by capability, latency, and cost. In manual mode, use only a useful subset of the saved pool; never force every saved model to run. Give agents distinct, concrete assignments and file ownership where relevant. Do not duplicate work to fill the limit. Pass the selected model explicitly to each spawn when supported, and report an unavailable model instead of silently substituting. The main model steps into substantive work only when I explicitly ask or no usable worker is available, and explains that exception.

Log each subagent call across all batches with target, model, distinct assignment or purpose, and outcome. Capture dispatch and observed completion times for each work interval. In the final answer, include a concise worker table and call list; label timing as dispatch-to-completion elapsed time unless the platform supplies actual active runtime. If no worker was available, say why. Do not claim cost savings without usage evidence.

Add `priority <balanced|speed|cost|quality>` to persistent settings. Add `/delegate start [--budget-tokens N] [--budget-usd N] <task>`, `runs`, `progress [id]`, `calls [id]`, `pause [id]`, `resume [id]`, `stop [id]`, and `diagnostics`. The checkpoint saves only a concise progress summary and assignment history across chats, not a full backlog. The coordinator uses it to continue assigning the next ready work to idle or reusable agents. Give each assignment an expected output, acceptance check, and optional file ownership. Reject duplicate or overlapping active assignments; send failed checks back for repair. Record every actual agent call, result, and dispatch-to-completion interval. Track provider-reported token use and USD cost when available. Check per-task budget estimates before dispatch and pause if actual usage needed for accounting is unavailable; describe this as an estimate check, not a guaranteed provider cap. Suggest models from observed outcomes, time, and cost with sample counts, while checking current availability and using an allowed fallback when a model fails. Diagnostics must distinguish local settings checks from live agent-tool capabilities that a local script cannot inspect.

Before each fresh spawn, check the run's idle agents and reuse a suitable one with `followup_task`. If all agents are busy, wait when a fresh spawn adds more overhead than value. Require a concrete `--new-agent-reason` for every additional agent after the first. A failed spawn must release its reserved distinct-agent slot. Keep the existing agent's model fixed for follow-up assignments. Test these rules with a temporary run.

Validate the skill and test the settings helper with temporary state files: auto/manual switching, preserving a manual pool, a six-agent maximum, rejecting 0 and 7, rejecting an unavailable model without mutation, and reset. Report the installed paths and exact invocation syntax.
````

### Claude Code creation prompt

````text
Create and install a personal Claude Code skill named `delegate` that becomes the `/delegate` command. Do the implementation now; do not merely explain it or stop after writing a plan. Use Python 3.11+ standard library for the settings helper. Preserve existing Claude settings and unrelated files.

Create ~/.claude/skills/delegate/SKILL.md and ~/.claude/skills/delegate/scripts/delegate.py, or use CLAUDE_CONFIG_DIR instead of ~/.claude when it is set. The skill frontmatter must include `name: delegate`, a concise description, an argument hint, and `disable-model-invocation: true`. Use `$ARGUMENTS` to receive text after `/delegate`. Resolve the helper relative to the skill directory using Claude Code's `${CLAUDE_SKILL_DIR}` substitution. Do not place this command in a Codex directory.
Also create ~/.claude/skills/delegate/scripts/run.py for local task checkpoints, agent and call history, progress, budgets, and diagnostics, using CLAUDE_CONFIG_DIR when set.

The Claude model selected for the main conversation remains the planner, router, integrator, and final reviewer. Workers are Claude Code subagents launched with the Agent tool. Save settings across local chats in the Claude configuration directory as delegate.json with version, mode (`auto` or `manual`), models, and max_agents (1 through 6). Default to auto mode and max_agents 3. Use Claude's model aliases `haiku`, `sonnet`, and `opus` for the manual pool; verify actual session availability at spawn time. Write settings atomically. Do not claim that Codex GPT model IDs work as Claude subagents without a separate provider integration.

Implement `/delegate auto [1-6]`, `/delegate select auto [1-6]`, `/delegate count <1-6>`, `/delegate select <haiku|sonnet|opus...>`, `/delegate add <models...>`, `/delegate remove <models...>`, `/delegate manual`, `/delegate models`, `/delegate status`, `/delegate reset`, and `/delegate off`. Treat any other argument as the task. Treat `/delegate goal <objective>` as a long-running task instruction with delegation; do not claim it creates Codex's native `/goal` mode.

For each activated task, maintain a backlog with dependencies and completion criteria. Use agents for substantive research, implementation, routine fixes, and verification work. After the first batch, inspect results and give each idle agent the next ready distinct assignment; continue through all batches until complete or genuinely blocked. Do not take over unfinished work in the main conversation merely because the first agents finished. Reuse or resume agents where supported. Never spawn more than the saved maximum, six distinct agents total, or the platform's lower limit; count sequential and nested workers too. This is a cap on distinct agents, not assignments. If agents cannot be resumed at the cap, report that limitation. In auto mode, choose Haiku for bounded routine work, Sonnet for general work, and Opus when complexity warrants it, subject to availability and the task's quality needs. In manual mode, choose a useful subset of saved aliases. Pass the alias in the Agent tool's per-invocation model parameter when available. Give every worker a distinct assignment; do not invent or duplicate work to fill the limit. Keep planning, routing, light integration, final verification, and the answer in the main conversation. The main model does substantive work only when I explicitly ask it to step in or no usable worker is available; explain that exception. Respect plan and review boundaries.

Record each Agent and subagent message or resume call across all batches, target, model, purpose, outcome, dispatch time, and observed completion time. End with a concise worker table and call list covering every work interval. Label wall time as dispatch-to-completion elapsed time unless actual active runtime is supplied. Do not invent timing or claim savings without usage evidence.

Add `priority <balanced|speed|cost|quality>` to saved settings. Add `/delegate start [--budget-tokens N] [--budget-usd N] <task>`, `runs`, `progress [id]`, `calls [id]`, `pause [id]`, `resume [id]`, `stop [id]`, and `diagnostics`. Save a concise progress checkpoint and assignment history across chats without persisting a full task backlog. For each Agent assignment, require a unique purpose, expected output, acceptance check, and optional file ownership. Reject duplicate or overlapping active assignments; route failed checks back for repair. Record actual Agent calls, completion intervals, and provider-reported usage or cost when available. Check estimates against a per-task budget before dispatch and pause when actual usage needed for the next dispatch is unavailable; never claim a provider-side hard cap. Use observed outcomes, elapsed time, and cost as advisory model signals with sample counts. Verify live alias availability, try another allowed alias after a failure, and clearly report the fallback. Diagnostics must say which live capabilities a local script cannot check.

Before a fresh Agent spawn, inspect idle agents and resume a suitable one. If all are busy, wait when another spawn adds more overhead than value. Require a concrete `--new-agent-reason` for every additional agent after the first, and release a reserved slot when a spawn fails. Keep a resumed agent's model unchanged. Test idle reuse, justified spawns, and failed-spawn accounting with temporary state.

Test the helper using temporary files: auto/manual switching, preserving the manual pool, rejecting 0 and 7, rejecting invalid model aliases without mutation, and reset. Verify Claude Code recognizes `/delegate` if authentication is available; if a live check is blocked, report the exact blocker. Report the installed paths and an example invocation.
````
