---
name: status
description: Use when the user wants an overview of all sub-project statuses, asks "what's the state of everything?", "show me project status", or types /status. Reads all _progress.md files and renders a summary table.
user_invocable: true
---

# /status — Sub-Project Status Overview

## Step 1 — Find all progress files

```bash
python -c "
import os, glob, re, json

projects_dir = os.path.join(os.getcwd(), 'projects')
if not os.path.isdir(projects_dir):
    print('NONE')
    exit(0)

results = []
for f in sorted(glob.glob(os.path.join(projects_dir, '*', '*_progress.md'))):
    txt = open(f, encoding='utf-8').read()
    name = os.path.basename(os.path.dirname(f))
    status_m = re.search(r'## Status:\s*(.+)', txt)
    status = status_m.group(1).strip() if status_m else 'UNKNOWN'
    pending = re.findall(r'- \[ \] (.+)', txt)
    done = re.findall(r'- \[x\] (.+)', txt, re.IGNORECASE)
    gotcha_m = re.search(r'## Key Gotcha\n(.+?)(?=\n## |\Z)', txt, re.DOTALL)
    gotcha = gotcha_m.group(1).strip()[:120] if gotcha_m else ''
    results.append({
        'name': name, 'status': status,
        'done': len(done), 'pending': len(pending),
        'next': pending[0].strip() if pending else '',
        'gotcha': gotcha,
        'file': f
    })

print(json.dumps(results))
" 2>&1
```

- `NONE` → "No `projects/` directory found. Run `project-index-manager` to set up sub-projects."
- `[]` → "No `_progress.md` files found under `projects/`."
- Results → proceed to Step 2.

## Step 2 — Render status table

Present as:

```
## Project Status — <today's date>

| Sub-Project | Status | Done | Pending | Next Action |
|---|---|---|---|---|
| **erc-adoption** | IN PROGRESS | 7 | 3 | Update stored procedure for Q2 rates |
| **amt-benchmark** | COMPLETE | 12 | 0 | — |
| **sub-app-config** | BLOCKED | 2 | 5 | Waiting on DB access from IT |
```

Then for any sub-project with `Key Gotcha` content, append:

```
### Key Gotchas
- **erc-adoption:** <gotcha text>
- **sub-app-config:** <gotcha text>
```

Ask: "Want to drill into any sub-project? (enter name or number)"

## Step 3 — Drill down (optional)

If user selects a sub-project, read its full `_progress.md` and present all Done/Pending items. Offer to also load its `_Index.md`.

## Notes

- Never reads raw `.jsonl` files.
- If a `_progress.md` has no Status line, show `UNKNOWN` and flag it.
