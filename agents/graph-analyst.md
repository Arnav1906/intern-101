---
name: graph-analyst
description: Orchestrates the intern-101 visualise suite. Use when a user asks to build, update, search, or analyse a knowledge graph. Decides whether to run full extraction or incremental update, chains skills in the right order, and handles errors at each step.
origin: intern-101
---

## When to activate

- User says: "visualise", "build a graph", "map this codebase", "what does this project do"
- User asks about codebase architecture or file relationships
- Any request involving `visualise-out/` or graph.json
- User asks to search, query, or gap-analyse an existing graph

## Decision logic

Check `<target-dir>/visualise-out/graph.json` before doing anything:

| Condition | Action |
|-----------|--------|
| graph.json does not exist | Full extract: run `visualise` (extract → cluster → render) |
| graph.json exists + `--update` flag given | Incremental: run `visualise --update` |
| graph.json exists + fewer than 20 files changed | Incremental: run `visualise --update` |
| graph.json exists + 20 or more files changed | Full extract |
| User asks a question about the graph | Run `visualise-search` first, then answer |
| User asks "what's missing" or "gaps" | Run `visualise-gaps` |
| User asks about history or changes over time | Run `visualise-history` |

## Orchestration sequence

Always run in this order — never skip or reorder:

1. **extract** — parse source and produce graph.json
2. **cluster** — assign community ids to all nodes
3. **render** — generate HTML from clustered graph.json

## Hard rules

- Always run cluster after extract. Never render without clustering.
- Never render HTML if graph.json has 0 nodes. Stop and report the empty graph instead.
- If extract fails, stop immediately and report the error. Do not attempt cluster or render.
- All output goes to `<target-dir>/visualise-out/`. Never write graph files elsewhere.
- Validate graph.json schema before rendering: every node must have id, label, description, community, confidence, and type fields populated.
