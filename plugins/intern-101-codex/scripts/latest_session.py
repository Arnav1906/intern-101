"""Print the latest matching actual Codex rollout path."""
import sqlite3
import sys
from lib.history_adapter import latest_session_path

if __name__ == "__main__":
    try:
        print(latest_session_path())
    except AttributeError:
        print("ERROR:Malformed or unsupported Codex history. "
              "Check the rollout records or select another supported session.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError, sqlite3.Error) as error:
        print("ERROR:" + str(error), file=sys.stderr)
        sys.exit(1)
