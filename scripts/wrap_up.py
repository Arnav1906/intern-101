"""Git status helper for the wrap-up skill."""

import sys
import subprocess
import argparse
from pathlib import Path


def _run_git(*args, cwd: Path) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, cwd=str(cwd)
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", "git not found"


def _is_repo(cwd: Path) -> bool:
    code, _, _ = _run_git("rev-parse", "--is-inside-work-tree", cwd=cwd)
    return code == 0


def _current_branch(cwd: Path) -> str:
    _, out, _ = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    return out or "unknown"


def _dirty_files(cwd: Path) -> list:
    _, out, _ = _run_git("status", "--porcelain", cwd=cwd)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines


def check_mode(cwd: Path) -> None:
    if not _is_repo(cwd):
        print("NO_REPO")
        return
    files = _dirty_files(cwd)
    if not files:
        print("CLEAN")
        return
    branch = _current_branch(cwd)
    print(f"DIRTY:{branch}")
    for f in files:
        print(f)


def diff_stat_mode(cwd: Path) -> None:
    code, out, err = _run_git("diff", "--stat", "HEAD", cwd=cwd)
    if code != 0:
        # fallback: unstaged only
        _, out, _ = _run_git("diff", "--stat", cwd=cwd)
    print(out if out else "(no diff output)")


def commit_mode(cwd: Path, message: str) -> None:
    # stage everything
    code, _, err = _run_git("add", "-A", cwd=cwd)
    if code != 0:
        print(f"FAILED:git add failed: {err}")
        return

    code, _, err = _run_git("commit", "-m", message, cwd=cwd)
    if code != 0:
        print(f"FAILED:{err or 'commit failed'}")
        return

    _, sha, _ = _run_git("rev-parse", "--short", "HEAD", cwd=cwd)
    print(f"COMMITTED:{sha}")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--diff-stat", action="store_true")
    group.add_argument("--commit", metavar="MESSAGE")
    args = parser.parse_args()

    cwd = Path.cwd()

    if args.check:
        check_mode(cwd)
    elif args.diff_stat:
        diff_stat_mode(cwd)
    elif args.commit:
        commit_mode(cwd, args.commit)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED:{e}", file=sys.stderr)
        sys.exit(1)
