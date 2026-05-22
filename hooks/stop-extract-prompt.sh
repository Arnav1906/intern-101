#!/usr/bin/env bash
set -euo pipefail

today="$(date +%Y-%m-%d)"
contexts_dir="${PWD}/chat-contexts"

# If chat-contexts/ doesn't exist, user doesn't use this feature — exit silently
if [[ ! -d "$contexts_dir" ]]; then
  exit 0
fi

# Check for any context file with today's date prefix
if ls "${contexts_dir}/${today}"*.md 2>/dev/null | grep -q .; then
  # Files found for today — exit silently
  exit 0
fi

# No files found for today — remind the user
echo "Tip: run /extract-today to save today's sessions before you go."
