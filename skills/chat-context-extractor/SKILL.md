---
name: chat-context-extractor
description: Reads a Claude Code .jsonl session transcript and produces a structured, searchable markdown context document. When no path is given, auto-locates the most recent session from ~/.claude/projects/ for the current working directory. Works on Windows, macOS, and Linux.
user_invocable: true
model: sonnet
---

# Chat Context Extractor

Processes a Claude Code `.jsonl` session into a condensed context document.

## Input

Path optionally provided via `{{ arguments }}`.

- **Path given:** use it directly.
- **No path:** run Step 0 to auto-locate the latest session.

---

## Step 0 — Auto-Locate Latest Session (only when no path given)

```bash
python -c "
import os, glob, sys

cwd = os.getcwd()

def path_to_hash(p):
    if sys.platform == 'win32':
        h = p.replace(':\\\\', '--').replace('\\\\', '-').replace('/', '-')
        if h: h = h[0].lower() + h[1:]
    else:
        h = p.replace('/', '-')
    return h

hash_try = path_to_hash(cwd)
claude_projects = os.path.join(os.path.expanduser('~'), '.claude', 'projects')
project_session_dir = None
for attempt in [hash_try, hash_try.lower()]:
    d = os.path.join(claude_projects, attempt)
    if os.path.isdir(d):
        project_session_dir = d
        break
if not project_session_dir:
    last = os.path.basename(cwd).lower().replace('_', '-')
    for name in os.listdir(claude_projects):
        if name.lower().endswith(last):
            project_session_dir = os.path.join(claude_projects, name)
            break
if not project_session_dir:
    print('ERROR: could not find project session dir for: ' + cwd)
    exit(1)
jsonl_files = glob.glob(os.path.join(project_session_dir, '*.jsonl'))
if not jsonl_files:
    print('ERROR: no .jsonl files in ' + project_session_dir)
    exit(1)
jsonl_files.sort(key=os.path.getmtime, reverse=True)
print(jsonl_files[0])
" 2>&1
```

Parse last non-empty line. If `ERROR:` → report and stop.

---

## Step 1 — Clean the Transcript

Run the cleaner (substitute the resolved path for `<path>`):

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/chat_context_extractor.py" "<path>"
```

Parse the last non-empty line of stdout as JSON.
If the line starts with `ERROR:` → report the error and stop.
If `turns` is empty → report "metadata-only or corrupted session" and stop.

---

## Step 2 — Dispatch Synthesis Agent

Using the **Agent tool**, invoke the `intern-101:chat-context-extractor` agent.

Pass the full JSON object from Step 1 as the agent's prompt, prefixed with:

> Synthesize a context document from this cleaned session JSON and write it to disk. JSON: `<paste full JSON here>`

Wait for the agent to return its confirmation block, then output it verbatim.

---

## Edge Cases

- Step 0 fails → report error, stop
- Step 1 produces `ERROR:` → report, stop
- Existing output file → agent appends `_v2`, `_v3` suffix
- Multiple session IDs in JSON → agent notes in Summary
