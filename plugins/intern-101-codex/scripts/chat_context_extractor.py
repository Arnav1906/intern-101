"""Print one complete original-schema cleaned Codex session."""
import json
import sqlite3
import sys
from lib.history_adapter import clean_session

if __name__ == "__main__":
    try:
        source = sys.argv[1] if len(sys.argv) > 1 else None
        print(json.dumps(clean_session(source), ensure_ascii=False))
    except AttributeError:
        print("ERROR:Malformed or unsupported Codex history. "
              "Check the rollout records or select another supported session.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError, sqlite3.Error) as error:
        print("ERROR:" + str(error), file=sys.stderr)
        sys.exit(1)
