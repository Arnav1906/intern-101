# Runtime and project files

Resolve the plugin root from the loaded skill's absolute path: `skills/<name>/SKILL.md`
is two directories below the plugin root. Its helper is `scripts/intern101.py`.
Use that installed helper, even when it lives in Codex's plugin cache. Do not
search the user's project for the plugin source or use another CLI's plugin root.

Commands work in PowerShell and POSIX shells:

```text
python "<plugin-root>/scripts/intern101.py" --project "<working-directory>" <command>
```

Use `python3` if that is the available Python executable. Python 3.9+ is required;
there are no third-party dependencies. Helpers return JSON. A nonzero exit with
`error` means report the error; do not interpret it as an empty session list.

The helper resolves a project root using `.intern101/config.json`, then `.git`,
then the supplied directory. All skills should use the same resolved root.
Session metadata must identify that root or a descendant directory. Only Codex
history is read. Session files and databases are opened read-only.

Optional project configuration at `.intern101/config.json`:

```json
{
  "codex_home": "auto",
  "contexts_dir": "chat-contexts"
}
```

`codex_home` uses the configured override, then `CODEX_HOME`, then `~/.codex`.
It can be an absolute path or a path relative to the project. No config is needed
for defaults. `contexts_dir` must remain inside the project.

Notes and `INDEX.md` are in `chat-contexts/`; progress files are under `projects/`.
Existing notes from other tools are readable. New extractions have `source: codex`.
Prepared JSON and synthesis inputs belong under `.intern101/` in the project.
Do not write into the installed plugin, Codex home, or another project's folder.

For history access problems run `doctor`. The supported readers handle legacy
rollouts, paginated completion records, and structurally compatible thread-item
databases. These storage formats can change between Codex releases. Report an
unsupported format explicitly rather than inventing a summary.
