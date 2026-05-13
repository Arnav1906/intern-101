---
name: project-index-manager
description: Use when a project directory has scattered files across multiple work domains with no clear organization, when starting a multi-domain project, or when a user asks to set up project indexes, progress files, or a routing index. Also use when updating _Index.md or _progress.md after completing work on a sub-project.
---

# Project Index Manager

## Overview

Transforms a scattered project directory into a self-documenting workspace by grouping work into named sub-projects, each with an `_Index.md` (what it is, key files, context pointers) and a `_progress.md` (status, done/pending checkboxes). A root `_Index.md` routes to everything. `CLAUDE.md` is wired to read the root index at every session start.

**Core principle:** Every sub-project is self-contained enough that a new Claude session can orient itself in under 30 seconds by reading one file.

---

## When to Use

- Files scattered across root, various folders, named by convention but ungrouped
- User asks to "organize the project", "set up indexes", or "make this navigable"
- Completing work on a sub-project → update its `_progress.md`
- New files added to a sub-project → update its `_Index.md`
- New sub-project emerges → add to `projects/`, root `_Index.md`, and CLAUDE.md

**When NOT to use:**
- Single-domain projects (just create one `_Index.md` at root)
- Projects already organized with their own conventions

---

## The Structure

```
project-root/
├── _Index.md                        ← root router (read every session)
├── CLAUDE.md                        ← wired to read _Index.md at start
├── restructure_progress.md          ← created during setup, tracks moves
│
├── projects/
│   ├── <sub-project-a>/
│   │   ├── <sub-project-a>_Index.md
│   │   ├── <sub-project-a>_progress.md
│   │   └── [all files belonging to this sub-project]
│   └── <sub-project-b>/
│       ├── <sub-project-b>_Index.md
│       ├── <sub-project-b>_progress.md
│       └── [...]
│
├── chat-contexts/                   ← session logs (shared, not in projects/)
├── [shared reference dirs]
└── archive/                         ← old/superseded work
```

---

## Phase 0 — Bootstrap `.intern101/` Helpers

Before doing anything else, check if `.intern101/find_project_dir.py` exists. If not, create it:

```bash
python -c "
import os
os.makedirs('.intern101', exist_ok=True)
open('.intern101/find_project_dir.py', 'w').write('''
import os, sys, glob

def find_project_dir(cwd=None):
    cwd = cwd or os.getcwd()
    def path_to_hash(p):
        if sys.platform == \"win32\":
            h = p.replace(\":\\\\\\\\\", \"--\").replace(\"\\\\\\\\\", \"-\").replace(\"/\", \"-\")
            if h: h = h[0].lower() + h[1:]
        else:
            h = p.replace(\"/\", \"-\")
        return h
    hash_try = path_to_hash(cwd)
    claude_projects = os.path.join(os.path.expanduser(\"~\"), \".claude\", \"projects\")
    for attempt in [hash_try, hash_try.lower()]:
        d = os.path.join(claude_projects, attempt)
        if os.path.isdir(d):
            return d
    last = os.path.basename(cwd).lower().replace(\"_\", \"-\")
    for name in os.listdir(claude_projects):
        if name.lower().endswith(last):
            return os.path.join(claude_projects, name)
    return None

if __name__ == \"__main__\":
    d = find_project_dir()
    if not d:
        print(\"ERROR: could not find project session dir for: \" + os.getcwd())
        sys.exit(1)
    print(d)
''')
print('bootstrapped')
" 2>&1
```

If output is `bootstrapped` or `.intern101/find_project_dir.py` already exists, proceed.

---

## Phase 1 — Discovery

1. Explore the full directory tree
2. Look for clustering signals: files sharing a naming prefix, folders belonging to one domain, chat-context docs describing distinct work, git history groupings
3. Name each cluster as a slug: `kebab-case`, describes the work domain not a technology
4. Present the proposed grouping to the user for confirmation before moving anything

**Good names:** `erc-adoption`, `amt-benchmark`, `sub-app-config`
**Bad names:** `sql-files`, `scripts`, `misc`

---

## Phase 2 — Scaffold + Move

Create `restructure_progress.md` at the project root first. Update it `[x]` after each completed step.

Execute moves per sub-project, one at a time. Verify source folder is empty before deleting.

**Folders that stay at root (never move into projects/):**
`chat-contexts/`, shared reference dirs, build artifacts, `.git/`, `.claude/`, config files, `archive/`

---

## Phase 3 — Populate Index Files

### `<name>_Index.md`
```markdown
# <Name> — Index

## What This Project Is
[2–3 sentences: problem being solved, outcome, current state]

## Key [Tables / SPs / APIs / Files] Involved
[bullet list of important named things]

## Files in This Folder
[bullet: filename — one-line description]

## Relevant Chat Contexts
[bullet: chat-contexts/YYYY-MM-DD_filename.md — what that session covered]
```

### `<name>_progress.md`
```markdown
# <Name> — Progress

## Status: [COMPLETE / IN PROGRESS / PENDING CONFIRMATION / BLOCKED]

## Done
- [x] [specific completed step]

## Pending
- [ ] [specific next action with blocker noted]

## Key Gotcha
[Most non-obvious thing about this sub-project]
```

**Populate from:** existing chat-context files, git log, existing docs. Never leave stubs empty.

---

## Phase 4 — Root `_Index.md`

Two sections:

**Sub-Projects Table:**
```markdown
| Sub-Project | What It Is | Index File |
|---|---|---|
| **<name>** | [one sentence summary + status] | [`projects/<name>/<name>_Index.md`] |
```

**Directories Without an Index:**
```markdown
| Directory | Go Here When... |
|---|---|
| `chat-contexts/` | You need full conversation history for prior work. |
| `archive/` | You need to understand what was tried and abandoned. |
```

Also add a **Root-Level Files** table for important non-directory files.

---

## Phase 5 — Wire CLAUDE.md

Add at the very top of `CLAUDE.md`:

```markdown
## Session Start — Read This First

**Always read [`_Index.md`](_Index.md) at the start of every session.**
It routes to all sub-project indexes and explains every directory.
```

---

## Session-End Automation

At the end of every session, invoke the `chat-context-extractor` skill with no arguments. It auto-locates the latest session, copies to `claudechats/`, extracts to `chat-contexts/`, updates `INDEX.md`, and appends to the matching sub-project `_Index.md`.

---

## Ongoing Maintenance

| Event | Action |
|---|---|
| Session ends with meaningful work | Run `chat-context-extractor` (no args) |
| Finish a task | Mark `[x]` in `_progress.md` |
| New file added | Add to `<name>_Index.md` → Files section |
| New sub-project emerges | Create folder, stubs, add row to root `_Index.md` |
| Status changes | Update Status line in `_progress.md` |

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Putting `chat-contexts/` inside a sub-project | Keep at root — shared across all sub-projects |
| Leaving stub Index files empty | Populate from chat-contexts and existing docs immediately |
| Naming sub-projects by technology | `sql-files/` is bad; `compositerates-logging/` is good |
| Moving build artifacts / `.git/` | Never — breaks paths and tooling |
| Not updating `_progress.md` after work | Future sessions waste time re-discovering state |
| Root `_Index.md` only covers sub-projects | Must also explain every non-project directory |
