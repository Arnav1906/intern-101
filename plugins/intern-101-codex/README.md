# Intern 101 for Codex

A standalone Codex Marketplace plugin for saving session context, resuming work, writing daily updates, and organizing project progress. It reads this project's Codex history and saves notes as project-local Markdown.

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start and skills](#quick-start-and-skills)
- [Configuration and history](#configuration-and-history)
- [Agents and hooks](#agents-and-hooks)
- [Uninstall](#uninstall)
- [Local development](#local-development)
- [References](#references)
- [License](#license)

## Requirements

Codex with plugin Marketplace support and Python **3.9+**. The runtime uses the standard library, with no pip dependencies or separate plugin API key. Sign in to Codex as usual; Codex uses its active model to synthesize summaries. Windows, macOS, and Linux are supported.

## Installation

Run in your terminal:

```sh
codex plugin marketplace add Arnav1906/intern-101 --sparse .agents/plugins --sparse plugins/intern-101-codex
codex plugin add intern-101@intern-101-codex
```

Start a new Codex session after installation. Alternatively, browse the configured marketplace through `/plugins` and install Intern 101.

The marketplace points to `plugins/intern-101-codex/`. Codex manages the installed package in its plugin cache. Sparse checkout limits the marketplace snapshot to the catalog and Codex package; actual Git network transfer depends on Git. The package contains its own skills, references, Python runtime, guide, and license.

## Quick start and skills

Run these in your Codex chat while working in the project:

```text
$intern-101:intern catch me up
$intern-101:intern save today's sessions
$intern-101:intern write my daily update
$intern-101:intern done for today
```

The dispatcher follows the relevant workflows in order. Save sessions before generating an update, and use wrap-up at the end of work. You can also invoke any skill directly:

| Invocation | Purpose |
| --- | --- |
| `$intern-101:intern` | Route your request to the appropriate skill. |
| `$intern-101:catchup` | Resume recent saved work and its next steps. |
| `$intern-101:extract-today` | Save today's new or continued project sessions. |
| `$intern-101:chat-context-extractor` | Save a selected session; defaults to the latest project session. |
| `$intern-101:daily-update` | Write an update from today's, yesterday's, or supplied notes. |
| `$intern-101:recall <query>` | Search saved notes for a topic and recover findings. |
| `$intern-101:status` | Show sub-project progress and pending work. |
| `$intern-101:wrap-up` | Review Git changes, optionally commit, and save today's sessions. |
| `$intern-101:project-index-manager` | Create or maintain project indexes and progress files. |

Context notes contain Summary, Accomplishments, useful Key Decisions & Findings, Next Steps, and Files Modified when available. `chat-contexts/INDEX.md` remains compatible with existing project notes. Catchup and recall can use saved notes from other agents; new raw-history extraction reads Codex only.

## Configuration and history

### Locations and precedence

No project configuration is required for defaults: history comes from `CODEX_HOME`, or `~/.codex`, and context notes go in `chat-contexts/`.

For custom locations, create `.intern101/config.json` in your project:

```json
{
  "codex_home": "D:/my-codex-home",
  "contexts_dir": "chat-contexts"
}
```

Set `codex_home` to your actual Codex home path. An explicit helper `--codex-home` argument takes priority over the configured path, followed by `CODEX_HOME` and `~/.codex`. Use `"auto"` to follow the environment/default. Relative configured paths resolve from the project root. The context output directory must remain inside that root.

The helper walks up from the working directory to find `.intern101/config.json` or `.git`, using the first matching ancestor; configuration wins when both occur in the same directory. Without either, it uses the supplied directory. Sessions must belong to that root or a descendant directory.

### Project output

Notes and `INDEX.md` live in the context directory. Prepared JSON and synthesis inputs live under `.intern101/`. Project organization creates a root `_Index.md`, sub-project index/progress files under `projects/`, and an instruction in `AGENTS.md` to read the index. Existing instructions are preserved.

Generated context stays in the project. The runtime opens Codex history files and databases read-only.

### Supported history

The reader supports legacy rollout JSONL messages, paginated completion records, and structurally compatible read-only `state_*.sqlite` / `thread_history_*.sqlite` schemas. These are Codex internals and can change. Unsupported sessions are reported as errors rather than treated as empty.

Archived sessions are opt-in; subagent histories are excluded from normal discovery. Days use the machine's local timezone and conversation timestamps. Unchanged conversations are skipped, continued sessions produce new notes, and daily updates use the latest snapshot per session for the selected date.

### Diagnostics

Resolve the installed plugin root from the loaded skill's location, then run:

```sh
python "<plugin-root>/scripts/intern101.py" --project "<project-directory>" doctor
```

Use `python3` if that is your available Python executable. Check the reported project root, Codex home, history availability, and configuration when session discovery fails. See [runtime guidance](references/runtime.md) and [synthesis guidance](references/synthesis.md) for the helper workflows.

## Agents and hooks

Codex's dispatcher selects sibling skills, and the active model synthesizes cleaned session snapshots directly. The package does not require Claude's specialist agents or subagent delegation.

The manifest declares an empty hooks object. Save sessions explicitly with `$intern-101:extract-today` or `$intern-101:wrap-up`. Wrap-up reviews Git changes and requires your authorization before committing; pushing is a separate action.

## Uninstall

Run in your terminal:

```sh
codex plugin remove intern-101@intern-101-codex
```

This removes the installed plugin and its local cache. You can also uninstall through `/plugins`. Start a new Codex session afterward.

To remove the marketplace source too:

```sh
codex plugin marketplace remove intern-101-codex
```

Your Codex history and project files remain, including the context directory, `.intern101/`, `_Index.md`, and sub-project index/progress files. Keep these for reference or another agent. To stop project-specific reminders, remove only the Intern 101 instruction added to `AGENTS.md`. Review notes and helper/configuration files before deleting any you no longer need, preserving unrelated instructions and project work.

See the [official Codex command reference](https://learn.chatgpt.com/docs/developer-commands) for plugin and marketplace management.

## Local development

From the repository checkout root:

```sh
codex plugin marketplace add .
codex plugin add intern-101@intern-101-codex
python tools/build_codex.py
```

Start a new session to load the installed skills. The builder creates a ZIP in `dist/` containing this standalone package, including its guide and MIT license; tests and Claude assets are excluded. Local development commands require the source repository, since the builder is not inside the installed plugin.

Marketplace is the normal installation route. Adding this repository's marketplace does not submit the plugin to the public directory; that is a separate publishing process.

## References

The separate manifest and marketplace layout follows the pattern used by [Superpowers](https://github.com/obra/superpowers). Official documentation: [Codex packaging](https://developers.openai.com/plugins/build/plugins), [Codex skills](https://learn.chatgpt.com/docs/build-skills), and [plugin commands](https://learn.chatgpt.com/docs/developer-commands).

## License

[MIT](LICENSE). Copyright (c) 2026 Arnav Bhalla.
