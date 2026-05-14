# Intern 101

A Claude Code plugin for working professionals, generally interns. Five skills that handle the repetitive parts of a work session: organizing a project directory, saving session context, picking up where you left off, and writing your daily update.

## Skills & Commands

| Skill / Command | What it does |
|---|---|
| `project-index-manager` | Sets up a `projects/` folder with `_Index.md` + `_progress.md` per sub-project and a root `_Index.md` router. Wires `CLAUDE.md` to read the index every session. |
| `chat-context-extractor` | Auto-finds the latest session `.jsonl`, copies it to `claudechats/`, extracts a structured summary to `chat-contexts/`, and updates the index. |
| `/catchup` | Session-start briefing — shows last 3 sessions, asks what to load, delivers a "where you left off" summary. |
| `/extract-today` | Finds all new sessions from today not yet extracted, asks for confirmation, batch-extracts them all. |
| `/daily-update` | Auto-reads today's session summaries and generates a 5–7 point plain-language status update for your supervisor. |
| `/recall <query>` | Searches past session titles and summaries for a keyword. Returns matching sessions with snippets. |
| `/status` | Shows all sub-projects' current status, pending items, and next actions in one table. |

## Install

### Option 1 — CLI (easiest)

```bash
claude plugin marketplace add Arnav1906/intern-101
```

Then restart Claude Code.

### Option 2 — npm

```bash
npm install -g intern-101
```

### Manual fallback

If the CLI command doesn't work, add to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "intern-101": {
      "source": { "source": "github", "repo": "Arnav1906/intern-101" }
    }
  },
  "enabledPlugins": { "Arnav1906@intern-101": true }
}
```

Then restart Claude Code. All skills will be available immediately.

## Requirements

- [Claude Code](https://claude.ai/code)
- Python 3.8+ (used by extraction scripts)
- Works on Windows, macOS, and Linux

## Recommended Workflow

```
# Start of day
/catchup                  → last 5 sessions, pick up where you left off
/status                   → one-page overview of all sub-project states

# During the day
/recall <topic>           → find past sessions on a topic before starting new work

# End of day
/extract-today            → save all today's sessions as context docs
/daily-update             → generate plain-language update for your supervisor
```

## Project Index Setup (one-time per project)

When starting on a messy codebase, invoke the `project-index-manager` skill:

> "Set up project indexes for this directory"

Claude will explore the project, identify natural work domains, create `projects/<name>/` folders with index and progress files, build a root `_Index.md` router, and wire `CLAUDE.md` to load it every session.

## Author

Arnav Bhalla
