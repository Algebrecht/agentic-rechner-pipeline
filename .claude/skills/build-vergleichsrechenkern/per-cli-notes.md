# Per-CLI notes — build-vergleichsrechenkern

The behavioral contract in `SKILL.md` is the install-neutral §6.7 body. It contains no
SDK call, API key, or CLI-specific front-matter; each CLI wraps it with its own delivery
mechanism but the contract does not change (§3.6).

## Claude CLI / Claude Code — VERIFIED target

This is the verified target. The body ships as a native Agent Skill at
`.claude\skills\build-vergleichsrechenkern\SKILL.md` (or `~\.claude\skills\...`) and is
invoked with `/build-vergleichsrechenkern` or by the trigger phrasing in the description.
Local stdio MCP for the toolbox is available via Claude MCP configuration; command target is
`python -m rechner_pipeline.toolbox.mcp_stdio`. Headless: `claude -p "..."` with appropriate
permission/MCP flags. (Exact shared project-file convention if a common `AGENTS.md` is used:
VERIFY.)

## GitHub Copilot CLI — VERIFY stub (not built)

No verified native `SKILL.md`. Install the procedure as `AGENTS.md` and/or
`.github\copilot-instructions.md`, with an optional custom agent/prompt when supported.
MCP supported; configure a local stdio toolbox command `python -m rechner_pipeline.toolbox.mcp_stdio`.
Headless: `copilot -p "..."` with `--allow-tool` / `--allow-all-tools` as policy permits.
Custom-command authoring beyond instructions/plugins, custom-agent config path/precedence,
and exact project/user MCP config path: VERIFY.

## Codex CLI — VERIFY stub (not built)

No verified native `SKILL.md`. Use `AGENTS.md` plus custom prompt content that embeds or
references the §6.7 body. Subagents available via `/codex/subagents`. MCP via Codex config
(local stdio server `python -m rechner_pipeline.toolbox.mcp_stdio`). Headless:
`codex exec "..."` with explicit workspace-write/sandbox/approval flags. Exact MCP stanza
and custom-prompt/slash-command authoring: VERIFY.

## OpenCode CLI — VERIFY stub (not built)

Use `.opencode\commands\build-vergleichsrechenkern.md` or `command` in `opencode.json`;
include/reference the same §6.7 body. Invoked `/build-vergleichsrechenkern`. Primary and
subagents via `opencode.json` or Markdown (`@agent`). MCP supported via local stdio command
`python -m rechner_pipeline.toolbox.mcp_stdio`; no remote MCP. Headless: `opencode run "..."`.
Exact headless subcommand/options: VERIFY.
