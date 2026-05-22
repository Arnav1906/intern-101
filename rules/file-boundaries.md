# File Boundaries

Always-on safety rule. All intern-101 skills must obey these constraints.

## Path safety

- Never write to any path outside the current working directory tree
- Resolve all paths before writing; reject any path containing `..` segments that escape the project root

## chat-contexts/

- Never overwrite an existing file in `chat-contexts/`
- Always generate a new unique filename using the `YYYY-MM-DD-HH-MM-<slug>.md` pattern
- If a filename collision occurs, append a counter suffix: `-2`, `-3`, etc.

## Deletions

- Never delete any file without explicit user confirmation in the same message
- "clean up" or "remove old files" is not sufficient — ask for confirmation and list affected paths

## graph output

- `visualise-out/` is the only allowed output directory for graph files
- Never write `graph.json` or any rendered HTML to the project root or any other directory
- If `visualise-out/` does not exist, create it before writing — do not fall back to another location
