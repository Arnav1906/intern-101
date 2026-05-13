---
name: recall
description: Use when the user wants to find past sessions related to a topic, asks "did we work on X before?", "find sessions about Y", or types /recall <query>. Always shows the 5 most recent sessions first, then searches if a query was given.
user_invocable: true
---

# /recall — Find Past Sessions

## Step 1 — Show 5 most recent sessions (always)

```bash
python -c "
import os, glob, re

ctx_dir = os.path.join(os.getcwd(), 'chat-contexts')
if not os.path.isdir(ctx_dir):
    print('NONE')
    exit(0)

files = sorted(
    [f for f in glob.glob(os.path.join(ctx_dir, '*.md')) if os.path.basename(f) != 'INDEX.md'],
    key=os.path.getmtime, reverse=True
)[:5]

for f in files:
    txt = open(f, encoding='utf-8').read(500)
    m = re.search(r'^# (.+)$', txt, re.MULTILINE)
    title = m.group(1) if m else os.path.basename(f)
    date_m = re.search(r'date:\s*(\S+)', txt)
    date = date_m.group(1) if date_m else os.path.basename(f)[:10]
    print(date + ' | ' + title + ' | ' + os.path.basename(f))
" 2>&1
```

- `NONE` → "No session history yet. Run `/extract-today` first." Stop.
- Lines returned → display as numbered list:

```
Recent sessions:
  1. YYYY-MM-DD — <Title>
  2. YYYY-MM-DD — <Title>
  ...
```

If `{{ arguments }}` is non-empty, proceed to Step 2 (search). Otherwise ask: "Open one (enter number), or type a search term."

**Wait for answer.** If user enters a number → jump to Step 4. If user enters text → treat as query and run Step 2.

## Step 2 — Search INDEX.md titles

```bash
python -c "
import os, re

query = r'{{ arguments }}'.strip().lower()
idx = os.path.join(os.getcwd(), 'chat-contexts', 'INDEX.md')
if not os.path.isfile(idx):
    print('NONE')
    exit(0)

rows = [l for l in open(idx, encoding='utf-8').readlines()
        if l.strip().startswith('|') and '---' not in l and 'Date' not in l]
matches = [r for r in rows if query in r.lower()]
print('\n'.join(matches) if matches else 'NONE')
" 2>&1
```

- `NONE` → "No title matches for '{{ arguments }}'. Want me to search inside file contents?"
- Matches → proceed to Step 3.

## Step 3 — Present search matches

Show matched rows as a numbered list (continuing from Step 1 numbering if helpful):

```
Found N session(s) matching "{{ arguments }}":

  1. YYYY-MM-DD — <Title>  [<filename>]
  2. YYYY-MM-DD — <Title>  [<filename>]
```

Ask: "Open one (enter number), or 'search content' to grep file bodies."

**Wait for answer.**

## Step 4 — Load chosen session or expand search

**If number entered:** Read that `chat-contexts/<filename>`, present `## Summary` and `## Key Decisions & Findings`. Offer to load full file.

**If "search content":**

```bash
python -c "
import os, glob, re

query = r'{{ arguments }}'.strip().lower()
ctx_dir = os.path.join(os.getcwd(), 'chat-contexts')
results = []
for f in sorted(glob.glob(os.path.join(ctx_dir, '*.md'))):
    if os.path.basename(f) == 'INDEX.md': continue
    txt = open(f, encoding='utf-8').read(3000)
    if query in txt.lower():
        m = re.search(r'^# (.+)$', txt, re.MULTILINE)
        title = m.group(1) if m else os.path.basename(f)
        snippet_m = re.search(r'.{0,60}' + re.escape(query) + r'.{0,60}', txt, re.IGNORECASE)
        snippet = snippet_m.group(0).strip() if snippet_m else ''
        results.append(os.path.basename(f) + ' | ' + title + ' | ...' + snippet + '...')
print('\n'.join(results) if results else 'NONE')
" 2>&1
```

Show results numbered. Ask which to open.

## Notes

- Step 1 always runs — recent sessions shown even with no query.
- Only reads from `chat-contexts/` — never raw `.jsonl` files.
- Case-insensitive throughout.
