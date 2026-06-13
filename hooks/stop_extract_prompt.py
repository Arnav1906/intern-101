#!/usr/bin/env python3
"""Remind the user to extract today's sessions if they haven't already."""
from datetime import datetime
from pathlib import Path


def main() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    contexts_dir = Path.cwd() / "chat-contexts"

    if not contexts_dir.is_dir():
        return

    if any(contexts_dir.glob(f"{today}*.md")):
        return

    print("Tip: run /extract-today to save today's sessions before you go.")


if __name__ == "__main__":
    main()
