"""Print today's new Codex session presentation records."""
import json
import sqlite3
import sys
from lib.history_adapter import todays_new_sessions

if __name__ == "__main__":
    try:
        print(json.dumps(todays_new_sessions(), ensure_ascii=False))
    except AttributeError:
        print("ERROR:Malformed or unsupported Codex history. "
              "Check the rollout records or select another supported session.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError, sqlite3.Error) as error:
        print("ERROR:" + str(error), file=sys.stderr)
        sys.exit(1)
