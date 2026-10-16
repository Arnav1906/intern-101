# Runtime and project files

Resolve `<plugin-root>` from the loaded skill's absolute installed path:
`skills/<name>/SKILL.md` is two directories below the plugin root. Run the
original-named helper in that root's `scripts/` directory from the user's
project working directory. Use the installed package, including when it lives
in Codex's plugin cache; do not search the project for a source checkout or use
another CLI's plugin root.

The command paths in the skills use this binding:

```text
python "<plugin-root>/scripts/catchup.py" 2>&1
```

Use `python3` if that is the available Python executable. Python 3.9+ is required;
there are no third-party runtime dependencies. Keep each skill's command
arguments and output/error handling. Bind `{{ arguments }}` to the user's
supplied arguments for that skill invocation; retain its meaning in each step.

The history helpers resolve the project from optional `.intern101/config.json`,
then `.git`, then the working directory. Codex home uses the configured
`codex_home` override, then `CODEX_HOME`, then `~/.codex`. Only Codex history is
read, and session files and databases are opened read-only. Report an unsupported
history format or missing usable rollout file as an error.

`latest_session.py` returns the latest matching actual rollout path.
`chat_context_extractor.py "<path>"` returns one complete cleaned-session JSON
object with the original fields, including `turns`, `files_modified`,
`project_root`, `total_user`, and `total_assistant`. `extract_today.py` returns
today's new sessions with their paths, UUIDs, times, and file sizes. No prompt
paging loop or persistent prepared/synthesis JSON files is part of this workflow.

## Native delegation

Read the packaged `agents/chat-context-extractor.md` verbatim and pass its
instructions to a native Codex subagent together with the complete cleaned
session JSON and the prefix prescribed by the skill. Keep host execution wiring
here; the packaged agent owns synthesis, document format, index updates, and its
confirmation block. See the [synthesis reference](synthesis.md).

Native subagents inherit the configured Codex model settings. Do not select a
model from the preserved Claude frontmatter or introduce a hardcoded OpenAI
model. For batch extraction, create one subagent task per confirmed session,
respect the host's concurrency limit, and collect every confirmation block.
If a slot is unavailable, wait for an active task before dispatching the next.

If native subagent tooling is unavailable, report the unmet delegation
requirement and stop. Do not synthesize in the parent or claim delegated success.

Saved Markdown context notes in the project can be read regardless of which
supported CLI produced them. The synthesis agent writes `chat-contexts/` and
`chat-contexts/INDEX.md` according to its packaged instructions. Do not write
into the installed plugin or Codex history.
