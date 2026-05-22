---
name: visualise-history
description: Use when the user wants to see how codebase architecture evolved over time, asks "how has the code changed since last sprint", "show me architectural history", or types /visualise-history. Requires git repository and /visualise first.
user_invocable: true
origin: intern-101
allowed-tools: [Read, Write, Bash]
---

# /visualise-history — Temporal Architecture History

Walk git history and snapshot the knowledge graph at each commit. Produces a time-slider HTML where you can scrub through time and see how your architecture evolved.

**Usage:**
- `/visualise-history` → last 10 commits
- `/visualise-history --commits 20` → last 20 commits
- `/visualise-history --since 2w` → commits from last 2 weeks
- `/visualise-history --since 2026-04-01` → commits since date

**Unique feature:** No competing plugin (including graphify) has architecture time-travel.

---

## Step 1 — Check prerequisites

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/history.py" check 2>&1
```

- If `GIT:False`: "This directory is not a git repository. `/visualise-history` requires git to walk commit history." Stop.
- If `HAS_GRAPH:False`: "No graph found. Run `/visualise` first to build the baseline graph." Stop.

---

## Step 2 — Parse arguments and get commit list

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/history.py" commits "{{ arguments }}" 2>&1
```

- If 0 commits: "No commits found for the given range." Stop.
- If >50 commits: "Found N commits. Processing all may take a while. Continue with all N, or reduce with `--commits 20`?" — wait for confirmation.
- Present the commit list to the user (SHA, date, message).

---

## Step 3 — Snapshot graph at each commit

For each commit in the list, extract a lightweight graph snapshot.

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/history.py" snapshot "<JSON array of commit lines from Step 2>" 2>&1
```

Pass the commit lines from Step 2 as a JSON array of strings (each line is `SHA|date|message`).

---

## Step 4 — Generate HTML time-slider

Read `history-template.html` (same directory as this SKILL.md). Replace the `SNAPSHOTS_JSON_PLACEHOLDER` token with the JSON array loaded in the next step, then write the resulting HTML to `visualise-out/graph_history.html`. The template uses D3.js v7 (CDN), renders a clickable timeline bar of commits, and shows a force graph for the selected commit.

Load all snapshots from `visualise-out/snapshots/`:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/history.py" prepare-data 2>&1
```

Read `history-template.html`, replace `SNAPSHOTS_JSON_PLACEHOLDER` with the content of `_history_tmpl.txt`, write to `visualise-out/graph_history.html`, then delete `_history_tmpl.txt` with `os.unlink(tmpl_path)`. The JSON is embedded inside `<script type="application/json">` so `</script>` sequences in commit messages cannot break out of the tag.

---

## Step 5 — Summary

```
Architecture history built.

  Commits analyzed: N
  Snapshots saved:  N  →  visualise-out/snapshots/

Output:
  visualise-out/graph_history.html  ← open in browser, use timeline to scrub history

Most structurally changed commits:
  <sha_short> <date> <message> (+N nodes, -N nodes)
  <sha_short> <date> <message> (+N nodes, -N nodes)

Tip: Use /visualise-diff <sha1> <sha2> for a detailed diff between any two commits.
```

Identify the 2–3 commits with the largest change in node count (|snap.n_nodes - prev.n_nodes|) and highlight them in the summary.

---

## Notes

- Snapshots are cached in `visualise-out/snapshots/` — re-running for the same commits is instant.
- The graph at each commit is a lightweight extraction (structural only, no semantic LLM pass) for speed.
- For a detailed semantic comparison between two commits, use `/visualise-diff`.
- Requires git to be installed and the directory to be a git repository.
