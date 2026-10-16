# Intern 101 for Claude Code

Save session context, resume unfinished work, write daily updates, and organize project progress in Claude Code. This package contains all nine skills, synthesis agents, Python helpers, rules, and the session reminder hook needed by its workflows.

## Requirements

Claude Code with plugin marketplace support and Python 3.9+ available as `python`. The helpers use the Python standard library and require no pip dependencies.

## Installation

Run these commands in a terminal:

```cmd
claude plugin marketplace add Arnav1906/intern-101 --sparse .claude-plugin plugins/intern-101-claude
claude plugin install intern-101@intern-101
```

Start a new Claude Code session after installing. In your project, run `/intern-101:intern` and describe what you need, such as “catch me up” or “save today's sessions”.

The supported sparse installation selects the repository marketplace catalog and this Claude package. The checked-out and installed runtime does not require or include the sibling Codex package. Git sparse checkout can retain top-level repository files and ancestor metadata; it does not guarantee that no Git objects from other paths transfer over the network.

## Existing installations

Refresh the marketplace and update the installed plugin to adopt the relocated layout:

```cmd
claude plugin marketplace update intern-101
claude plugin update intern-101@intern-101
```

Existing marketplace checkouts are not automatically converted to sparse checkout by a catalog update. To use the documented sparse checkout, remove and re-add the marketplace using the sparse installation command above:

```cmd
claude plugin marketplace remove intern-101
claude plugin marketplace add Arnav1906/intern-101 --sparse .claude-plugin plugins/intern-101-claude
claude plugin install intern-101@intern-101
```

## Project files and history

The original nine prompts, synthesis instructions, helper contracts, and workflow order are preserved. Claude reads Claude Code history. Saved Markdown context notes and indexes live in your project's `chat-contexts/` directory and can also be read by a compatible Codex installation. Project organization retains its existing confirmation steps before moving files or committing work.

## License

MIT. See [LICENSE](LICENSE).
