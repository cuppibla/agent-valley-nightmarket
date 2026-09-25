"""Apply or undo the three edits through the page's own door, from a terminal.

    uv run python scripts/edits.py apply 1        # EDIT ONE
    uv run python scripts/edits.py apply 1 2 3    # all three
    uv run python scripts/edits.py undo           # back to as shipped
    uv run python scripts/edits.py tower on|off   # name / un-name the tower in .env

Handy for the capture rig and for checking a chapter without re-walking the
ladder. Needs the Night Market running.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from walk import _env_engine_from_file, edit, edit_three, env_engine, recomment, uncomment, undo_three  # noqa: E402

APPLY = {
    1: lambda: edit("stage/wire.py", "upstream", uncomment("queue.send_realtime("), must_change=False),
    2: lambda: edit("stage/wire.py", "downstream", uncomment("if event.interrupted:"), must_change=False),
    3: lambda: edit("stage/stalls.py", "order_snack", edit_three, must_change=False),
}
UNDO = {
    1: lambda: edit("stage/wire.py", "upstream", recomment("queue.send_realtime("), must_change=False),
    2: lambda: edit("stage/wire.py", "downstream", recomment("if event.interrupted:"), must_change=False),
    3: lambda: edit("stage/stalls.py", "order_snack", undo_three, must_change=False),
}


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    verb, rest = args[0], args[1:]
    if verb == "apply":
        for n in (int(x) for x in rest or ["1", "2", "3"]):
            APPLY[n]()
            print(f"  EDIT {n} applied")
    elif verb == "undo":
        for n in (int(x) for x in rest or ["3", "2", "1"]):
            UNDO[n]()
            print(f"  EDIT {n} undone")
    elif verb == "tower":
        on = rest and rest[0] == "on"
        env_engine(_env_engine_from_file() if on else None)
        print("  tower named" if on else "  tower un-named")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
