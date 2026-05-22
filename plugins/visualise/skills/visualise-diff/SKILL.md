---
name: visualise-diff
description: Use when the user wants to compare codebase architecture between two git commits or points in time, asks "what changed architecturally", "what was added or removed", or types /visualise-diff. Requires /visualise-history snapshots first.
user_invocable: true
origin: intern-101
allowed-tools: [Read, Write, Bash]
---

# /visualise-diff — Architecture Diff

Compare the knowledge graph between two git commits (or two snapshot files) and produce a color-coded HTML diff report. Shows new nodes, removed nodes, community shifts, and edge changes.

**Usage:**
- `/visualise-diff HEAD~5 HEAD` → last 5 commits worth of changes
- `/visualise-diff abc1234 def5678` → specific commit SHAs
- `/visualise-diff snapshot-A.json snapshot-B.json` → explicit snapshot files

**Key difference from graphify:** No competing plugin has architecture diff. This is code review for architecture, not just code.

---

## Step 1 — Parse arguments and locate snapshots

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/diff.py" resolve <ref_A> <ref_B> 2>&1
```

- If `USAGE_ERROR`: "Usage: `/visualise-diff <commit-or-snapshot-A> <commit-or-snapshot-B>`" Stop.
- If `A:NEED_SNAPSHOT:<sha>` or `B:NEED_SNAPSHOT:<sha>`: "Snapshot not found for `<sha>`. Run `/visualise-history --commits N` first to generate snapshots." Stop.
- If `ERROR:...`: "Could not resolve ref `<ref>`. Use a valid git SHA, branch name, or `HEAD~N`." Stop.

---

## Step 2 — Compute diff

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/diff.py" diff "<A path from Step 1>" "<B path from Step 1>" 2>&1
```

---

## Step 3 — Generate HTML diff report

Read `diff-template.html` (same directory as this SKILL.md). Copy it verbatim to `visualise-out/graph_diff.html`. The template reads `.diff_data.json` from the same directory at runtime and renders the diff as a color-coded table (green = added, red = removed, yellow = community-shifted).

---

## Step 4 — Summary

```
Architecture diff complete.

  A: <sha> (<date>) — <message>
  B: <sha> (<date>) — <message>

  Nodes added:     +N  (new modules, functions, concepts introduced)
  Nodes removed:   -N  (deleted or renamed)
  Community shifts: ~N  (same code, different architectural role)
  Edges added:     +N
  Edges removed:   -N

Output:
  visualise-out/graph_diff.html  ← open in browser for full diff report

<highlight any nodes that are both added-to-B and were previously in "god node" territory — new hubs>
<highlight any removed nodes that had degree > 5 — significant deletions>
```

---

## Notes

- Both snapshots must exist in `visualise-out/snapshots/` — run `/visualise-history` first.
- Community shifts indicate the same code has changed its architectural relationships, even if the code itself didn't change.
- A node appearing as "removed" with high prior degree is architecturally significant — it was a hub.
- The diff HTML reads `.diff_data.json` from the same directory; keep both files together.
