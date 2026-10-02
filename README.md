# Intern 101

A productivity plugin for interns and working professionals using Claude Code or Codex. Save session context, resume unfinished work, write daily updates, and organize project progress.

Each agent has its own installation and history reader. Saved Markdown notes and project indexes live in your project, so either agent can use them to pick up previous work.

Start with `/intern-101:intern` in Claude Code or `$intern-101:intern` in Codex and describe what you need.

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Skills](#skills)
- [Configuration and project files](#configuration-and-project-files)
- [Agents](#agents)
- [Hooks](#hooks)
- [Uninstall](#uninstall)
- [Development and architecture](#development-and-architecture)
- [Author](#author)
- [License](#license)

## Requirements

- [Claude Code](https://code.claude.com/docs/en/overview) or [Codex](https://learn.chatgpt.com/docs/plugins), with plugin Marketplace support.
- Python **3.9+**, available as `python` for the Claude scripts and hook. Codex skills can use `python3` if that is your Python executable.
- Windows, macOS, or Linux. The Python helpers use the standard library; no pip dependencies or separate plugin API key are needed. Sign in to your chosen agent as usual.

## Installation

Run the commands for your agent in a terminal.

### Claude Code

```sh
claude plugin marketplace add Arnav1906/intern-101
claude plugin install intern-101@intern-101 --scope user
```

This installs the plugin for your user account. For a repository-wide or local-only installation, run from that project and replace `--scope user` with `--scope project` or `--scope local`. Start a new Claude Code session after installing.

### Codex

```sh
codex plugin marketplace add Arnav1906/intern-101 --sparse .agents/plugins --sparse plugins/intern-101-codex
codex plugin add intern-101@intern-101-codex
```

The Codex marketplace installs the standalone package under `plugins/intern-101-codex/`. Start a new Codex session after installing. You can also browse the configured marketplace through `/plugins`.

See the [Codex guide](plugins/intern-101-codex/README.md) for history compatibility, diagnostics, and local installation. The [Claude plugin guide](https://code.claude.com/docs/en/discover-plugins) and [Codex command reference](https://learn.chatgpt.com/docs/developer-commands) describe the native plugin commands.

## Quick start

Run these inside your agent's chat while working in the project.

### Claude Code

```text
/intern-101:intern catch me up
/intern-101:intern save today's sessions
/intern-101:intern write my daily update
/intern-101:intern done for today
```

### Codex

```text
$intern-101:intern catch me up
$intern-101:intern save today's sessions
$intern-101:intern write my daily update
$intern-101:intern done for today
```

Use catchup at the start of work, recall when you need a past decision, and wrap-up when you finish. Save sessions before generating a daily update. Wrap-up reviews Git changes, offers an optional commit, and saves today's sessions; commits require your authorization.

## Skills

Both installations provide these nine skills. The `intern` dispatcher selects the right workflow from your request, or you can invoke a skill directly.

| Skill | Purpose | Claude Code | Codex |
| --- | --- | --- | --- |
| `intern` | Route a natural-language request to the relevant skill. | `/intern-101:intern` | `$intern-101:intern` |
| `catchup` | Resume from recent saved sessions, decisions, and next steps. | `/intern-101:catchup` | `$intern-101:catchup` |
| `extract-today` | Save today's new project sessions as context notes. Codex also detects continued sessions. | `/intern-101:extract-today` | `$intern-101:extract-today` |
| `chat-context-extractor` | Save one selected session; defaults to the latest project session. | `/intern-101:chat-context-extractor` | `$intern-101:chat-context-extractor` |
| `daily-update` | Write a concise supervisor update from saved sessions or supplied notes. | `/intern-101:daily-update` | `$intern-101:daily-update` |
| `recall` | Find saved work about a topic and recover useful findings. | `/intern-101:recall <query>` | `$intern-101:recall <query>` |
| `status` | Summarize sub-project progress, pending work, and next actions. | `/intern-101:status` | `$intern-101:status` |
| `wrap-up` | Review Git changes, optionally commit, and save today's sessions. | `/intern-101:wrap-up` | `$intern-101:wrap-up` |
| `project-index-manager` | Create and maintain project indexes and progress files. | `/intern-101:project-index-manager` | `$intern-101:project-index-manager` |

## Configuration and project files

### Claude Code

The native install command manages plugin settings. User settings live in `~/.claude/settings.json`; project and local settings live in `.claude/settings.json` and `.claude/settings.local.json` respectively.

For advanced manual configuration, merge these entries into the appropriate settings file, preserving existing entries:

```json
{
  "extraKnownMarketplaces": {
    "intern-101": {
      "source": { "source": "github", "repo": "Arnav1906/intern-101" }
    }
  },
  "enabledPlugins": { "intern-101@intern-101": true }
}
```

Use the installation commands to download the plugin. Settings entries alone are not a replacement for installation.

The Claude reader finds project transcripts under `~/.claude/projects/`. Run skills from your project directory; saved context goes in `chat-contexts/`. This implementation has no custom Claude history or output-directory configuration file. Project organization adds instructions to `CLAUDE.md` to read the root index.

### Codex

Default history comes from `CODEX_HOME`, or `~/.codex` when that variable is unset. Default context output is `chat-contexts/`. No project configuration is needed for these defaults.

For custom locations, create `.intern101/config.json` in your project:

```json
{
  "codex_home": "D:/my-codex-home",
  "contexts_dir": "chat-contexts"
}
```

Set `codex_home` to your actual Codex home path. A helper's explicit `--codex-home` argument takes priority over the configured path, followed by `CODEX_HOME` and `~/.codex`. Use `"auto"` to follow the environment/default. Relative configured paths resolve from the project root, and `contexts_dir` must stay inside that project.

The configuration file or Git repository identifies the project root; otherwise the supplied working directory is used. Project organization adds instructions to `AGENTS.md` to read the root index. See the [Codex guide](plugins/intern-101-codex/README.md#configuration-and-history) for detailed history support.

### Shared project output

| File or directory | Purpose |
| --- | --- |
| `chat-contexts/` | Saved Markdown session notes and their `INDEX.md`. Codex can use a configured context directory instead. |
| `_Index.md` | Root index linking work domains and shared files. |
| `projects/<name>/` | Sub-project index and progress files alongside any agreed project organization. |
| `.intern101/` | Project-local helpers for Claude; configuration and prepared/synthesis inputs for Codex. |
| `CLAUDE.md` / `AGENTS.md` | Instructions to load project indexes in the relevant agent. |

Context notes record summaries, accomplishments, useful decisions, next steps, and modified files when available. Both agents can read compatible saved notes; each new extraction reads its own agent's raw history. Codex reads history files and databases without modifying them.

## Agents

Claude Code includes two specialist agents:

| Agent | Role and reason for inclusion |
| --- | --- |
| [`session-manager`](agents/session-manager.md) | Coordinates catchup, recall, status, and daily-update workflows, choosing how much context to load and which skills to chain. |
| [`chat-context-extractor`](agents/chat-context-extractor.md) | Turns cleaned session JSON into a structured note and updates indexes. Keeping synthesis separate lets the extractor skill handle transcript discovery and cleaning before handing over the relevant conversation. |

The extractor **skill** prepares the input and invokes the extractor **agent**. The agent summarizes that input directly, avoiding a recursive call back to the skill.

Codex performs routing and synthesis through its own skills and Python helper. Its standalone package uses the active Codex model and does not require these Claude agents or subagent delegation.

## Hooks

### Claude Code: bundled Stop reminder

Claude loads the hook from [`hooks/hooks.json`](hooks/hooks.json) with the installed plugin. Its configuration is:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/stop_extract_prompt.py\""
          }
        ]
      }
    ]
  }
}
```

At a Stop event, the Python hook prints an extraction reminder when the current working directory has `chat-contexts/` but no note dated today. Otherwise it stays silent. Run `/intern-101:extract-today` or `/intern-101:wrap-up` to save sessions.

The configuration above is already bundled; no additional settings entry is needed. See the [Claude manifest reference](https://code.claude.com/docs/en/plugins-reference) for hook loading.

### Codex: explicit wrap-up

The Codex manifest declares an empty hooks object. Use `$intern-101:wrap-up` or `$intern-101:extract-today` to save sessions explicitly.

## Uninstall

### Claude Code

```sh
claude plugin uninstall intern-101@intern-101 --scope user
```

For project or local installations, run from that project with `--scope project` or `--scope local`. Repeat for each installed scope, then start a new session. You can also uninstall through Claude's `/plugin` browser.

To remove the marketplace too:

```sh
claude plugin marketplace remove intern-101
```

Removing a Claude marketplace uninstalls any remaining plugins from it. If you previously downloaded the npm package, remove that copy separately with `npm uninstall -g intern-101`.

For manual settings, remove this plugin's `enabledPlugins` entry and its marketplace entry if no longer needed. Older instructions used the incorrect `Arnav1906@intern-101` key; remove that legacy entry if present. Remove any manually added Stop hook running `stop-extract-prompt.sh` or `stop_extract_prompt.py`, preserving other hooks and settings.

### Codex

```sh
codex plugin remove intern-101@intern-101-codex
```

This removes the installed plugin and its local cache. You can also uninstall through `/plugins`. Start a new session afterward. To remove the marketplace source too:

```sh
codex plugin marketplace remove intern-101-codex
```

### Project files after uninstall

Your agent session history, saved notes, indexes, progress files, and `.intern101/` remain. Keep them for reference or another agent. To stop project-specific reminders, remove only the Intern 101 instructions added to `CLAUDE.md` or `AGENTS.md`. Review saved notes and helper/configuration files before deleting any you no longer need; preserve actual project work.

## Development and architecture

The root contains the Claude package; the Codex package is self-contained:

```text
intern-101/
  .claude-plugin/                 Claude manifest and marketplace
  skills/                        Nine Claude skills
  agents/                        Claude workflow and synthesis agents
  rules/                         Claude output and file-operation guidance
  hooks/                         Claude Stop hook configuration and scripts
  scripts/                       Claude Python helpers
  .agents/plugins/marketplace.json
  plugins/intern-101-codex/
    .codex-plugin/plugin.json    Codex manifest
    skills/                      Nine Codex skills
    references/                  Runtime and synthesis instructions
    scripts/                     Codex Python CLI and history readers
    README.md
    LICENSE
  tools/build_codex.py           Codex ZIP builder
  LICENSE
```

Skills describe the workflow; Python helpers handle history and file operations, and the host model synthesizes the summaries. Claude resolves helpers through `CLAUDE_PLUGIN_ROOT`; Codex resolves them from its installed skill location.

From the repository root, build the standalone Codex ZIP:

```sh
python tools/build_codex.py
```

The archive in `dist/` includes the Codex manifest, skills, references, runtime, guide, and MIT license. Tests and Claude assets are excluded. See the [Codex development guide](plugins/intern-101-codex/README.md#local-development) for local Marketplace installation. The guides document the current implementation; additional CLI agents are not yet supported.

## Author

Arnav Bhalla

## License

[MIT](LICENSE). Copyright (c) 2026 Arnav Bhalla.
