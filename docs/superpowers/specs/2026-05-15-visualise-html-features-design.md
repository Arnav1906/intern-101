# Design: visualise HTML — Sidebar + Filter Panel

**Date:** 2026-05-15
**Scope:** `skills/visualise/graph-template.html` + `skills/visualise/SKILL.md`. Two new interactive features added to the HTML template, plus skill documentation updated to reflect them.

---

## Feature 1 — Collapsible Right Sidebar

### Behaviour
- Clicking a node slides in a right sidebar (30% width). The graph area shrinks to 70%.
- A `❮` toggle button sits on the left edge of the sidebar. Clicking it collapses the sidebar to a thin strip and the graph snaps back to full width. `❯` re-expands it.
- Clicking a node while the sidebar is collapsed re-opens it.
- Clicking the same node again or pressing Escape closes the sidebar.
- Clicking a different node while the sidebar is open updates it in place (no close/reopen animation).

### Panel content (per node)
| Field | Source | Notes |
|---|---|---|
| Label / ID | `node.label \|\| node.id` | Title, styled as god-node if in `meta.god_nodes` |
| Type | `node.type` | e.g. `stored_procedure`, `file`, `concept` |
| Community | `node.community` | Shown as colored badge matching graph color |
| Degree | `node.degree` | Raw number |
| Confidence | `node.confidence` | `EXTRACTED` / `INFERRED` / `AMBIGUOUS` with color coding |
| Source file | `node.source_file` | Shown only if present |
| Description | `node.description` | Shown only if present |
| Connected nodes | computed from `links` | Listed as clickable names; clicking jumps focus + centers that node |

### Animation
- Slide-in: CSS `transition: width 200ms ease`. No JS animation library.
- Graph SVG `width` is a CSS variable updated on open/close.

---

## Feature 2 — Floating ⚙ Filter Panel

### Trigger
- A ⚙ gear icon overlaid on the graph area (top-right, `position: absolute`).
- Click opens/closes a floating panel anchored below the icon.
- Clicking outside the panel (but not on the ⚙) closes it.

### Panel contents

**Communities section**
- One pill per community, colored to match graph.
- Active: full color. Inactive: grey with strikethrough text.
- Toggling a community: its nodes opacity → 0, edges to/from those nodes opacity → 0. Instant, no animation.
- State stored in a `Set<number>` of hidden community IDs.

**Edge confidence section**
- Three checkboxes: `EXTRACTED`, `INFERRED`, `AMBIGUOUS`.
- All on by default.
- Unchecking hides edges of that confidence type.

**Edge labels toggle**
- Single checkbox, off by default.
- When on: shows `edge.relation` text as a `<text>` element at edge midpoint.
- Labels are clipped/hidden when too short to read (< 20px edge length).

### Filter interaction with search
- The existing search box (`#search`) filters by node name substring.
- Community + confidence filters stack on top of the search filter (AND logic).
- A hidden node is never shown by search.

---

## Feature 3 — SKILL.md Updates

### `skills/visualise/SKILL.md`

**Step 7 description** — update to document the two new interactive features so users know what the generated `graph.html` supports:

> The generated `graph.html` includes:
> - Node search/filter (existing)
> - Zoom/pan (existing)
> - Community color legend (existing)
> - **Collapsible right sidebar** — click any node to see its full detail (type, community, degree, confidence, source file, description, connected nodes). Connected node names are clickable to jump focus. `❮/❯` button collapses/expands the panel.
> - **Floating ⚙ filter panel** — gear icon (top-right of graph area) opens a panel to toggle communities on/off, filter edges by confidence (EXTRACTED/INFERRED/AMBIGUOUS), and show/hide edge relation labels.

No changes to Step 7's Python/JS logic — this is documentation only.

**Step 8 completion message** — add the two features to the "open in browser" line so users know to look for them:

> `visualise-out/graph.html` ← open in browser (sidebar, filters, zoom/pan)

---

## Architecture

### Files changed
| File | Change |
|---|---|
| `skills/visualise/graph-template.html` | Add sidebar + filter panel (all JS/CSS inline) |
| `skills/visualise/SKILL.md` | Update Step 7 description + Step 8 completion message |

### No changes to
- Python extraction logic (Steps 1–6 in SKILL.md)
- `graph.json` schema — all needed fields already exist
- Any other skill file

### State variables (JS)
```
selectedNode      — currently selected node object | null
sidebarCollapsed  — boolean
hiddenCommunities — Set of community IDs
hiddenConfidence  — Set of confidence strings
showEdgeLabels    — boolean
filterPanelOpen   — boolean
```

---

## Out of scope
- Minimap, export PNG/SVG, layout modes — explicitly deferred.
