# Intern 101 for Codex

A standalone Codex marketplace plugin. It reads Codex's session history for the
active project and saves work context, daily updates, and project progress as
project-local Markdown. Python 3.9+ is required; no pip dependencies or separate
API key are needed. Codex performs the synthesis using its active model.

## Install from this repository's marketplace

After these files are available on GitHub:

```text
codex plugin marketplace add Arnav1906/intern-101 --sparse .agents/plugins --sparse plugins/intern-101-codex
codex plugin add intern-101@intern-101-codex
```

Alternatively, add the marketplace in Codex's `/plugins` browser, choose the
Intern 101 Codex marketplace, and install Intern 101. Restart an existing session
if the new skills are not visible.

The marketplace points only to `plugins/intern-101-codex/`. Sparse checkout keeps
the marketplace snapshot limited to its catalog and this package. It does not
promise selective Git network transfer. The installed plugin contains no Claude
manifests, agents, session readers, or hooks.

Codex manages the installed skill and script files in its plugin cache. These
files operate against the active project; generated context files remain in that
project. There is no manual installer or copy into `.agents/skills`.

## Use

```text
$intern-101:intern catch me up
$intern-101:extract-today
$intern-101:daily-update
$intern-101:recall authentication
$intern-101:status
$intern-101:wrap-up
```

`$intern-101:chat-context-extractor` handles one selected session. `$intern-101:project-index-manager`
organizes sub-project indexes and progress, with a project `AGENTS.md` entry.
These skills can also activate from matching natural-language requests.

New notes contain Summary, Accomplishments, optional Key Decisions & Findings,
Next Steps, and Files Modified. `chat-contexts/INDEX.md` remains compatible with
the existing project files. Notes from other tools can be used for catchup and
recall; new raw history extraction reads Codex only.

## Configuration and history compatibility

Defaults use `CODEX_HOME`, or `~/.codex`, and save under `chat-contexts/`.
For a custom location, create `.intern101/config.json` in the project:

```json
{
  "codex_home": "D:/my-codex-home",
  "contexts_dir": "chat-contexts"
}
```

An explicit `--codex-home` helper argument overrides configuration. Relative
configured paths resolve from the project root. The output directory must remain
inside that root. A configuration file also identifies the root of a project
without Git. Otherwise the nearest Git root is used, falling back to the supplied
directory.

The reader supports legacy JSONL messages, paginated rollout completion records,
and compatible read-only `state_*.sqlite` / `thread_history_*.sqlite` schemas.
The JSONL and SQLite layouts are Codex internals and can change. Unsupported
sessions are reported as errors, not silently treated as empty. Archived sessions
are opt-in and subagent histories are excluded from normal project discovery.
Days are computed using the machine's local timezone and conversation timestamps.
Repeated extraction skips unchanged conversations; continued sessions produce
new notes and daily updates use the newest snapshot per session on that date.

For diagnostics, resolve the plugin path from the loaded skill and run:

```text
python "<plugin-root>/scripts/intern101.py" --project "<project-directory>" doctor
```

The first release uses explicit wrap-up. No lifecycle hook is automatically
enabled. Git commit operations require the wrap-up skill's user authorization.

## Local development

From the repository root:

```text
codex plugin marketplace add .
codex plugin add intern-101@intern-101-codex
python -m unittest discover -s tests/codex -v
python tools/build_codex.py
```

The optional ZIP contains the same standalone Codex plugin for review or public
submission. The normal user installation route is Marketplace. Adding a custom
marketplace does not publish this plugin in OpenAI's curated public directory;
that requires a separate submission.

The package layout follows the separate Codex manifest and marketplace catalog
pattern used by [Superpowers](https://github.com/obra/superpowers). References:
[Codex packaging](https://developers.openai.com/plugins/build/plugins) and
[Codex skills](https://learn.chatgpt.com/docs/build-skills).
