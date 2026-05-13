---
name: chat-context-extractor
description: Reads a Claude Code .jsonl session transcript and produces a structured, searchable markdown context document. When no path is given, auto-locates the most recent session from ~/.claude/projects/ for the current working directory. Works on Windows, macOS, and Linux.
user_invocable: true
---

# Chat Context Extractor

Processes a Claude Code `.jsonl` session transcript into a condensed, searchable markdown context document.

## Input

Path optionally provided via `{{ arguments }}`.

- **Path given:** use it directly.
- **No path:** run Step 0 to auto-locate the latest session.

---

## Step 0 — Auto-Locate Latest Session (only when no path given)

If `.intern101/find_project_dir.py` exists, run:

```bash
python -c "
import os, glob, sys
sys.path.insert(0, '.intern101')
from find_project_dir import find_project_dir
d = find_project_dir()
if not d:
    print('ERROR: could not find project session dir for: ' + os.getcwd())
    sys.exit(1)
files = sorted(glob.glob(os.path.join(d, '*.jsonl')), key=os.path.getmtime, reverse=True)
if not files:
    print('ERROR: no .jsonl files in ' + d)
    sys.exit(1)
print(files[0])
" 2>&1
```

If `.intern101/find_project_dir.py` does not exist, use the full fallback:

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

Parse last non-empty line. If `ERROR:` → report and stop. Otherwise use as source path.

---

## Step 1 — Parse the JSONL

```bash
python -c "
import json, re, os, sys
from datetime import datetime, timezone

path = r'{{ arguments }}'.strip().strip('\"').strip(\"'\")

try:
    lines = open(path, 'r', encoding='utf-8').readlines()
except UnicodeDecodeError:
    lines = open(path, 'r', encoding='utf-8', errors='replace').readlines()

session_id = ''
model = ''
custom_title = ''
first_ts = ''
last_ts = ''
user_turns = []
assistant_turns = []
files_referenced = set()
sessions_seen = set()

TOOL_KEEP = {'Read','Write','Bash','Edit','Grep','Glob','Agent','ExitPlanMode','AskUserQuestion','WebFetch','WebSearch'}

def summarise_input(name, inp):
    if name == 'Read': return inp.get('file_path', '')
    if name in ('Write','Edit'):
        fp = inp.get('file_path', '')
        desc = inp.get('description', '')
        return fp + (' [' + desc[:60] + ']' if desc else '')
    if name == 'Bash':
        return inp.get('description','') or inp.get('command','')[:120]
    if name == 'Grep':
        return 'pattern=' + str(inp.get('pattern',''))[:60] + ' path=' + str(inp.get('path',''))[:60]
    if name == 'Glob':
        return str(inp.get('pattern','')) + ' in ' + str(inp.get('path',''))[:60]
    if name == 'Agent':
        return (inp.get('description','') or inp.get('prompt',''))[:100]
    if name in ('WebFetch','WebSearch'):
        return (inp.get('url','') or inp.get('query',''))[:100]
    return json.dumps(inp)[:120]

def extract_file_refs(name, inp):
    refs = []
    for key in ('file_path','path'):
        v = inp.get(key,'')
        if v and isinstance(v, str) and len(v) > 1: refs.append(v)
    if name == 'Bash':
        cmd = inp.get('command','')
        found = re.findall(r'(?:[A-Za-z]:[\\\\/]|[\\\\/])[^\s\"\'<>|]+\.[a-zA-Z0-9]{1,10}', cmd)
        refs.extend(found[:5])
    return refs

def ts_to_hhmm(ts):
    if not ts: return '??:??'
    try:
        dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
        return dt.astimezone(timezone.utc).strftime('%H:%M')
    except: return ts[11:16] if len(ts) >= 16 else '??:??'

def ts_to_date(ts):
    if not ts: return ''
    try:
        dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
        return dt.strftime('%Y-%m-%d')
    except: return ts[:10] if len(ts) >= 10 else ''

SKIP = {'[request interrupted by user]','continue','continue.','ok','okay','done','proceed','continue from where you left off.','continue from where you left off'}

def is_img(t): return bool(re.match(r'^\[image\s*[:#]', t, re.IGNORECASE))

def clean(txt):
    for pat in [r'<command-name>.*?</command-name>', r'<command-message>.*?</command-message>',
                r'<command-args>.*?</command-args>', r'<local-command-stdout>.*?</local-command-stdout>',
                r'<[a-z][a-z0-9_-]*(?:\s[^>]*)?>.*?</[a-z][a-z0-9_-]*>']:
        txt = re.sub(pat, '', txt, flags=re.DOTALL)
    return txt.strip()

for raw in lines:
    raw = raw.strip()
    if not raw: continue
    try: obj = json.loads(raw)
    except: continue
    if obj.get('isSidechain', False): continue
    t = obj.get('type','')
    ts = obj.get('timestamp','')
    if ts:
        if not first_ts or ts < first_ts: first_ts = ts
        if not last_ts or ts > last_ts: last_ts = ts
    sid = obj.get('sessionId','')
    if sid: sessions_seen.add(sid); session_id = sid
    if t == 'custom-title': custom_title = obj.get('customTitle',''); continue
    if t not in ('user','assistant'): continue
    msg = obj.get('message',{})
    if not isinstance(msg, dict): continue
    content = msg.get('content',[])
    if t == 'assistant':
        if not model: model = msg.get('model','')
        texts, uses = [], []
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict): continue
                ct = item.get('type','')
                if ct == 'text': texts.append(item.get('text',''))
                elif ct == 'tool_use':
                    name = item.get('name','')
                    inp = item.get('input',{}) or {}
                    if name in TOOL_KEEP:
                        uses.append({'name': name, 'summary': summarise_input(name, inp)})
                        for r in extract_file_refs(name, inp): files_referenced.add(r)
        elif isinstance(content, str): texts.append(content)
        combined = ' '.join(x for x in texts if x.strip())
        if combined.strip() or uses:
            assistant_turns.append({'ts': ts, 'hhmm': ts_to_hhmm(ts), 'text': combined[:800], 'tool_uses': uses})
    elif t == 'user':
        if isinstance(content, str):
            v = clean(content)
            if v.lower() not in SKIP and not is_img(v): user_turns.append({'ts': ts, 'hhmm': ts_to_hhmm(ts), 'text': v[:600]})
        elif isinstance(content, list):
            texts = [clean(i.get('text','')) for i in content if isinstance(i,dict) and i.get('type')=='text']
            combined = ' '.join(x for x in texts if x)
            if combined.strip() and combined.strip().lower() not in SKIP and not is_img(combined.strip()):
                user_turns.append({'ts': ts, 'hhmm': ts_to_hhmm(ts), 'text': combined[:600]})

import json as _json
print(_json.dumps({
    'session_id': session_id, 'custom_title': custom_title, 'model': model,
    'first_ts': first_ts, 'last_ts': last_ts, 'date': ts_to_date(first_ts),
    'user_turns': user_turns, 'assistant_turns': assistant_turns,
    'files_referenced': sorted(files_referenced), 'session_count': len(sessions_seen),
    'project_root': os.getcwd(),
    'total_user': len(user_turns), 'total_assistant': len(assistant_turns),
}))
" 2>&1
```

When called from Step 0, substitute the auto-located path for `{{ arguments }}`.

Parse last non-empty line as JSON. Stop if empty turns.

---

## Step 2 — Infer Title and Slug

1. Use `custom_title` if present (convert to kebab-case)
2. Otherwise derive from first 3 non-trivial human messages + key filenames
3. Produce 3–6 word kebab-case slug and title-cased readable title

---

## Step 3 — Output Paths

Use `project_root` from parsed data (always `os.getcwd()`, not the `.jsonl` directory).

- Output: `<project_root>/chat-contexts/<date>_<slug>.md`
- Index: `<project_root>/chat-contexts/INDEX.md`
- Version with `_v2`, `_v3` if file exists

```bash
python -c "import os; os.makedirs(r'<output_dir>', exist_ok=True); print('ready')"
```

---

## Step 4 — Condensed Transcript

Merge and sort all turns by `ts`. If total > 60, keep first 20 + last 20 with `*(... N turns omitted ...)` separator.

User: `### [HH:MM] Human\n<text>`
Assistant: `### [HH:MM] Assistant\n<text truncated 400 chars>\n> [Tool] summary`

---

## Step 5 — Build Document

```
---
session_id: <id>
date: <date>
model: <model>
source_file: <path>
tags: [3-6 tags]
---

# <Title>

## Summary
<2-3 sentences: goal from first 3 human messages + outcome from last 3 assistant turns>

## Key Topics
<Specific bullet list>

## Files & Resources Referenced
<Bullets from files_referenced. Group if >15. Skip /tmp and system paths.>

## Key Decisions & Findings
<Concrete conclusions useful months later>

## Important Code / SQL / Queries
<Only if notable — fenced blocks. Omit section if nothing stands out.>

## Conversation (Condensed)
<transcript>
```

---

## Step 6 — Write Document

Use Write tool to save to output path.

---

## Step 7 — Update INDEX.md

Read existing `INDEX.md`. Skip if filename already present. Create if missing:

```markdown
# Chat Context Index

| Date | Title | Key Topics | File |
|------|-------|------------|------|
```

Append row: `| <date> | <Title> | <top 3-4 tags> | \`<filename>\` |`

---

## Step 8 — Update Sub-Project _Index.md

Check if `<project_root>/projects/` exists. If yes, match session slug/tags against sub-project folder names. For each match, append to `_Index.md` → "Relevant Chat Contexts" section:

```
- `chat-contexts/<date>_<slug>.md` — <Title>
```

---

## Step 9 — Confirm

```
Context document saved:  <path>
INDEX.md updated:        <path>
Sub-project updated:     <projects/<name>/_Index.md> or "none matched"
Session: <id> | Date: <date> | Turns: <N> human, <N> assistant
```

---

## Edge Cases

- Step 0 fails → report error, stop
- No turns → report "metadata-only or corrupted"
- Multiple session IDs → note in Summary
- `isSidechain: true` → already skipped
- Existing output file → version `_v2`, `_v3`
- No `files_referenced` → omit that section
- No `projects/` dir → skip Step 8
