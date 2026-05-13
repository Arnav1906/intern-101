---
name: extract-today
description: Use when the user wants to save all of today's Claude sessions as context documents, says "extract today's sessions", or types /extract-today. Scans ~/.claude/projects/ for new .jsonl files from today, checks which are already extracted, and asks for confirmation before processing.
user_invocable: true
---

# /extract-today — Batch Extract All New Sessions for Today

## Step 1 — Find today's new sessions

```bash
python -c "
import os, glob, re, json, sys
from datetime import datetime

cwd = os.getcwd()

# Use helper if bootstrapped
project_session_dir = None
helper = os.path.join(cwd, '.intern101', 'find_project_dir.py')
if os.path.isfile(helper):
    sys.path.insert(0, os.path.join(cwd, '.intern101'))
    from find_project_dir import find_project_dir
    project_session_dir = find_project_dir(cwd)
else:
    def path_to_hash(p):
        if sys.platform == 'win32':
            h = p.replace(':\\\\', '--').replace('\\\\', '-').replace('/', '-')
            if h: h = h[0].lower() + h[1:]
        else:
            h = p.replace('/', '-')
        return h
    hash_try = path_to_hash(cwd)
    claude_projects = os.path.join(os.path.expanduser('~'), '.claude', 'projects')
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

# Collect already-extracted session IDs from chat-contexts/ frontmatter
known_ids = set()
ctx_dir = os.path.join(cwd, 'chat-contexts')
if os.path.isdir(ctx_dir):
    for md in glob.glob(os.path.join(ctx_dir, '*.md')):
        try:
            content = open(md, encoding='utf-8').read(500)
            m = re.search(r'session_id:\s*([a-f0-9\-]{36})', content)
            if m: known_ids.add(m.group(1))
        except: pass

today = datetime.now().strftime('%Y-%m-%d')
results = []
uuid_re = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
for f in glob.glob(os.path.join(project_session_dir, '*.jsonl')):
    mtime = datetime.fromtimestamp(os.path.getmtime(f))
    if mtime.strftime('%Y-%m-%d') != today: continue
    stem = os.path.splitext(os.path.basename(f))[0]
    if not uuid_re.match(stem): continue
    if stem in known_ids: continue
    size_kb = round(os.path.getsize(f) / 1024)
    results.append({'path': f, 'uuid': stem, 'mtime': mtime.strftime('%H:%M'), 'size_kb': size_kb})

results.sort(key=lambda x: x['mtime'])
print(json.dumps(results))
" 2>&1
```

Parse last non-empty line as JSON.

- `ERROR:` → report and stop.
- `[]` → "No new sessions found for today. All `.jsonl` files are already extracted or none exist." Stop.

## Step 2 — Present list and ask for confirmation

```
Found N new session(s) from today:

  #  Time   Size    UUID
  1  09:14  42 KB   f4fa97f5-...
  2  11:30  18 KB   9d5fbcf9-...

Extract all? Or enter numbers to skip (e.g. "skip 2"):
```

**Wait for answer before proceeding.**

- "yes" / "all" / enter → process all
- "skip N" → remove and process rest
- "no" / "cancel" → stop

## Step 3 — Extract each confirmed session

For each confirmed session, invoke the `chat-context-extractor` skill with the full `.jsonl` path. Process one at a time, chronological order. After each:

```
✓ [HH:MM] Extracted → chat-contexts/<date>_<slug>.md
```

## Step 4 — Summary

```
Extracted N session(s) for <today>:
  chat-contexts/<date>_<slug1>.md
  chat-contexts/<date>_<slug2>.md

INDEX.md updated. Sub-project _Index.md files updated where matched.
```

## Notes

- Sessions matched as "new" by UUID not appearing in existing frontmatter `session_id` fields.
- Files < 5 KB are likely metadata-only — flag: "Session #N is very small (X KB). Include anyway?"
- Only processes today's files. For older sessions, use `chat-context-extractor` directly with a path.
