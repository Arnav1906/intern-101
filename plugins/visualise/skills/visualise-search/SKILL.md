---
name: visualise-search
description: Use when the user wants to search the knowledge graph by description without knowing exact node names, asks "find nodes related to X", "what concepts are in the graph about Y", or types /visualise-search. Requires /visualise first.
user_invocable: true
origin: intern-101
allowed-tools: [Read, Bash]
model: opus
---

# /visualise-search — Semantic Node Search

Find nodes in the knowledge graph using natural language — no need to know exact node names. Ranks results by conceptual relevance.

**Usage:**
- `/visualise-search "stored procedure adoption"` → top nodes matching that concept
- `/visualise-search "authentication flow" --top 10` → top 10 results
- `/visualise-search "error handling" --community 3` → search within community 3 only

**Key difference from graphify:** graphify's BFS/DFS require the exact node name. This skill finds nodes from any description.

---

## Step 1 — Load graph.json

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/search.py" load 2>&1
```

- If `NOTFOUND`: "No graph found in `visualise-out/`. Run `/visualise` first to build the graph." Stop.
- Note the loaded node/edge counts.

---

## Step 2 — Parse arguments

Parse query and flags from `{{ arguments }}` directly: extract the quoted string as the query, `--top N` as result count (default 5), `--community N` as community filter (default: none).

- If query is empty: "Usage: `/visualise-search \"your query here\"`" Stop.

---

## Step 3 — Load and prepare nodes

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/search.py" prepare [--community <N>] 2>&1
```

Output is a JSON array of nodes with a `search_text` field for each. Use it in Step 4 for semantic ranking.

---

## Step 4 — Semantic ranking

You now have the full node list with `search_text` for each node, and the query `"<QUERY from Step 2>"`.

**Rank the nodes by semantic relevance to the query.** Do not just do keyword matching — use your understanding of the concepts to assess how closely each node relates to the query.

Consider:
- Nodes whose label directly names the query concept (highest relevance)
- Nodes in the same domain or used by/with the query concept
- Nodes that implement, configure, or reference the query concept
- Nodes with source files suggesting relevance (e.g., a file named `auth.py` is relevant to "authentication")

Select the top `<TOP from Step 2>` most relevant nodes. For each, prepare a 1-sentence explanation of **why** it's relevant to the query.

---

## Step 5 — Present results

Format results as:

```
Search: "<query>"  →  top N results

  1. NodeLabel  [community C · degree D]
     File: relative/source/file.py
     Why: <1-sentence relevance explanation>

  2. NodeLabel  [community C · degree D]
     File: relative/source/file.py
     Why: <1-sentence relevance explanation>

  ...
```

Then offer:
- "Explore a node? Use `/visualise-search` with the exact label, or ask me to show its neighbors."
- "Not what you were looking for? Try rephrasing your query."

---

## Step 6 — Show neighbors (if user asks to explore a node)

If the user selects a node to explore, load its neighbors from `graph.json`:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/visualise/search.py" neighbors "<node_id>" 2>&1
```

Present the neighbor list formatted as a clear table with relation type and confidence.

---

## Notes

- This skill ranks nodes using Claude's semantic understanding — it will correctly surface relevant nodes even when the query uses different terminology than the node labels.
- For large graphs (>500 nodes), Claude will sample the most plausible candidates before ranking to stay within context.
- Results improve with a more detailed `/visualise` run that captures richer node rationale during semantic extraction.
