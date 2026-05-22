# Graph Conventions

Always-on rule. Applies to the visualise skill and graph-analyst agent.

## Output location

All visualise output goes to `<target-dir>/visualise-out/`. No exceptions.

## graph.json schema

```json
{
  "nodes": [
    {
      "id": "string — unique identifier",
      "label": "string — short display name",
      "description": "string — one-sentence summary",
      "community": "integer — cluster id assigned during clustering step",
      "confidence": "EXTRACTED | INFERRED | AMBIGUOUS",
      "type": "string — node category, e.g. file, concept, skill, agent"
    }
  ],
  "edges": [
    {
      "source": "string — node id",
      "target": "string — node id",
      "label": "string — relationship description",
      "weight": "number — 0.0 to 1.0"
    }
  ]
}
```

## confidence values

- `EXTRACTED` — directly present in source material
- `INFERRED` — derived from context or structure
- `AMBIGUOUS` — uncertain; requires human verification

Only these three values are valid. Reject or flag any other value.

## Ordering

1. Extract → produces graph.json
2. Cluster → assigns community ids to all nodes
3. Render → produces HTML

Never skip or reorder steps. Never render HTML without a valid graph.json present. A valid graph.json must have at least one node and all required fields populated.
