# Intern 101

A standalone Claude Code plugin for interns and working professionals. Handles the repetitive parts of a work session — session catchup, daily updates, end-of-day wrap-up, project organization, and interactive codebase knowledge graphs.

**Single entry point:** just type `/intern` and describe what you need. No need to remember skill names.

---

## Quick Start

```
/intern I'm starting work — what was I doing?   → catchup
/intern done for today                           → wrap-up (git check + extract)
/intern write my daily update                    → daily-update
/intern map this codebase                        → visualise
```

Or invoke skills directly if you prefer.

---

## Skills

### `/intern` — Dispatcher

Understands natural language and routes to the right skill. Use this when you're not sure which skill you need.

```
/intern <anything>
```

Examples that work:
- "where was I last session" → `/catchup`
- "I'm done for today" → `/wrap-up`
- "what did I do this week" → `/daily-update`
- "find sessions about authentication" → `/recall`
- "show me all project statuses" → `/status`
- "build a graph of this repo" → `/visualise`

---

### Session Management

| Skill | What it does |
|---|---|
| `/catchup` | Shows last 5 sessions, asks what to load, delivers a "where you left off" summary |
| `/extract-today` | Finds all new sessions from today not yet saved, confirms, batch-extracts them |
| `chat-context-extractor` | Extracts a single `.jsonl` session into a structured markdown context doc. Auto-locates the latest session if no path given. Use when you want to extract one specific session rather than today's batch. |
| `/daily-update` | Reads today's extracted sessions and generates a 5–7 point plain-language update for your supervisor |
| `/recall <query>` | Searches past session titles and summaries for a keyword, returns matching sessions with snippets |
| `/status` | Shows all sub-projects' current status, pending items, and next actions in one table |
| `/wrap-up` | End-of-day: checks git status → prompts to commit if needed → extracts today's sessions |

---

### Project Organization

| Skill | What it does |
|---|---|
| `project-index-manager` | Organizes a messy project into named sub-projects, each with `_Index.md` + `_progress.md`. Wires `CLAUDE.md` to load the index every session. Invoke by description: *"set up project indexes"* |

---

### Knowledge Graph (`/visualise` suite)

| Skill | What it does |
|---|---|
| `/visualise [path]` | Builds an interactive HTML knowledge graph — AST + semantic extraction, Louvain community detection, god-node identification, confidence audit trail (`EXTRACTED` / `INFERRED` / `AMBIGUOUS`) |
| `/visualise-search <query>` | Finds graph nodes by natural language — no need to know exact names |
| `/visualise-gaps` | Lists isolated (undocumented/disconnected) nodes; `--draft` auto-generates stub docs for each |
| `/visualise-history` | Walks git history, snapshots the graph at each commit, generates a time-slider HTML |
| `/visualise-diff` | Color-coded diff between two snapshots — shows added, removed, and shifted nodes/edges |

---

## Recommended Workflow

```
# Start of day
/catchup                         → pick up where you left off
/status                          → one-page overview of all sub-projects

# During the day
/recall <topic>                  → find past sessions before starting new work
/visualise                       → map the codebase architecture
/visualise-search <query>        → find relevant nodes without knowing exact names

# End of day
/wrap-up                         → git check + optional commit + session extraction in one flow
```

---

## Install

### Option 1 — CLI

```bash
claude plugin marketplace add Arnav1906/intern-101
```

Restart Claude Code. All skills available immediately.

### Option 2 — npm

```bash
npm install -g intern-101
```

### Manual

Add to `~/.claude/settings.json`:

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

---

## Requirements

- [Claude Code](https://claude.ai/code)
- Python 3.8+
- Windows, macOS, and Linux supported

**For `/visualise` skills only:**
```bash
pip install networkx==3.3 python-louvain==0.16
```

---

## End-of-Day Hook (optional)

Adds a passive reminder to extract sessions when you close Claude without using `/wrap-up`. Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      { "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-extract-prompt.sh\"" }
    ]
  }
}
```

---

## Architecture

```
intern-101/
  skills/
    intern/              ← dispatcher: routes all natural language to the right skill
    catchup/
    chat-context-extractor/  ← single-session extractor (used by extract-today internally)
    daily-update/
    extract-today/
    project-index-manager/
    recall/
    status/
    wrap-up/

  plugins/
    visualise/
      skills/            ← visualise, visualise-search, visualise-gaps, visualise-history, visualise-diff
      assets/            ← HTML templates (graph, diff, history)

  agents/
    graph-analyst.md     ← orchestrates visualise suite with judgment (full vs incremental, sequencing)
    session-manager.md   ← orchestrates session skills (catchup + recall + daily-update flows)

  rules/
    output-format.md     ← daily-update format, context filename convention
    file-boundaries.md   ← no path traversal, no overwrite protection
    graph-conventions.md ← visualise-out/ layout, graph.json schema, extract→cluster→render order

  hooks/
    hooks.json           ← Stop event → stop-extract-prompt.sh
    stop-extract-prompt.sh

  scripts/
    lib/
      utils.py           ← CLAUDE_PLUGIN_ROOT resolution, path helpers, file I/O
      session.py         ← INDEX.md parsing, session file ops, slugify
      graph.py           ← graph.json load/save/query
    catchup.py
    chat_context_extractor.py
    daily_update.py
    extract_today.py
    project_index_manager.py
    recall.py
    status.py
    wrap_up.py
    visualise/
      extract.py         ← AST + semantic extraction → graph.json
      cluster.py         ← Louvain community detection
      render.py          ← graph.json + template → graph.html
      search.py
      gaps.py
      diff.py
      history.py
```

Each skill is a thin instruction layer — all Python logic lives in `scripts/`. Skills call scripts via `python "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"`, which makes scripts testable independently and keeps SKILL.md files focused on flow, not implementation.

---

## Author

Arnav Bhalla
