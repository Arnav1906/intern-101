"""Extract structured JSON from a Claude Code .jsonl session file."""

import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", "").strip())
                elif block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input", {})
                    if name == "Write" and "file_path" in inp:
                        parts.append(f"[Write] {inp['file_path']}")
                    elif name == "Edit" and "file_path" in inp:
                        parts.append(f"[Edit] {inp['file_path']}")
                    elif name == "Bash" and "command" in inp:
                        cmd = inp["command"][:120].replace("\n", " ")
                        parts.append(f"[Bash] {cmd}")
        return "\n".join(p for p in parts if p)
    return ""


def parse_jsonl(jsonl_path: Path) -> list:
    turns = []
    with jsonl_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message", {})
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "")
            content = msg.get("content", "")
            text = _extract_text(content)
            if text:
                turns.append({"role": role, "text": text})
    return turns


def _files_modified(turns: list) -> list:
    files = []
    seen = set()
    for t in turns:
        if t["role"] != "assistant":
            continue
        for m in re.finditer(r'\[(Write|Edit)\] (.+)', t["text"]):
            path = m.group(2).strip()
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _first_user_message(turns: list) -> str:
    for t in turns:
        if t["role"] == "user" and t["text"].strip():
            return t["text"].strip()
    return ""


def _generate_title_hint(first_msg: str) -> str:
    """Fallback title hint — LLM sub-agent will derive the real title."""
    first_line = first_msg.split("\n")[0].strip()
    first_line = re.sub(r"[#*`]", "", first_line).strip()
    return first_line[:80] or "Untitled Session"


def _extract_tags(title: str, files: list) -> str:
    words = re.findall(r'[a-zA-Z]{4,}', title.lower())
    exts = {Path(f).suffix.lstrip(".") for f in files if Path(f).suffix}
    tags = list(dict.fromkeys(words))[:5]
    tags += [e for e in sorted(exts) if e and e not in tags]
    return ", ".join(tags) if tags else "session"


def _extract_assistant_skeleton(text: str) -> str:
    """Keep tool call lines + up to 2 preceding prose lines each, plus opening lines."""
    lines = text.split("\n")
    to_include: set[int] = set()

    # Opening lines give intent context
    for i in range(min(3, len(lines))):
        to_include.add(i)

    for i, line in enumerate(lines):
        if re.match(r'\s*\[(Write|Edit|Bash)\]', line):
            to_include.add(i)
            for j in range(max(0, i - 2), i):
                to_include.add(j)

    kept = [lines[i].strip() for i in sorted(to_include) if i < len(lines)]
    return "\n".join(l for l in kept if l)


def _build_transcript(turns: list, max_chars: int = 20000) -> str:
    """Work-skeleton transcript: all user messages + assistant tool calls with context."""
    parts = []
    total = 0

    for t in turns:
        if t["role"] == "user":
            entry = f"user: {t['text'][:1000]}"
        else:
            skeleton = _extract_assistant_skeleton(t["text"])
            if not skeleton:
                continue
            entry = f"assistant: {skeleton}"

        if total + len(entry) > max_chars:
            parts.append("...[truncated: session exceeded extraction limit]")
            break
        parts.append(entry)
        total += len(entry)

    return "\n\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path", help=".jsonl session file path")
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl_path).resolve()
    if not jsonl_path.exists():
        print(f"ERROR:file not found: {jsonl_path}", file=sys.stderr)
        sys.exit(1)

    session_id = jsonl_path.stem
    turns = parse_jsonl(jsonl_path)
    if not turns:
        print(f"ERROR:no readable turns in {jsonl_path}", file=sys.stderr)
        sys.exit(1)

    first_msg = _first_user_message(turns)
    title_hint = _generate_title_hint(first_msg)
    date = datetime.fromtimestamp(jsonl_path.stat().st_mtime).strftime("%Y-%m-%d")
    files = _files_modified(turns)
    tags = _extract_tags(title_hint, files)
    transcript = _build_transcript(turns)

    print(json.dumps({
        "session_id": session_id,
        "date": date,
        "title_hint": title_hint,
        "files_modified": files,
        "tags": tags,
        "transcript": transcript,
        "turn_count": len(turns),
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
