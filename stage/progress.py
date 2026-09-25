"""How the Night Market knows which lantern to light.

Same idea as the Archive's: read the learner's code (comments stripped first —
the 👉 comment contains the very call we look for), and pair every code fact
with a counter the process kept during the last call, which cannot be fooled.

    lantern 1   a live model named          + a call in stage.db from the workbench
    lantern 2   send_realtime in upstream   + chunks rode the belt on the last call
    lantern 3   interrupted in downstream   + an interrupted reached the page
    lantern 4   create_task in order_snack  + the last order returned in under half a second
    lantern 5   .env names a tower          + a call was filed and something recalled
"""

from __future__ import annotations

import importlib
import inspect
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)
_last_good: dict[str, Any] | None = None


# stage.memory and stage.door are NOT here: the service holds one memory
# service instance and one call registry for its whole life, and both must
# keep their class identity across calls.
FRESH = ("stage.wire", "stage.agent", "stage.stalls", "stage.state")


def fresh(name: str = "stage.wire", tries: int = 4):
    """Import the learner's code as it is on disk right now, and return `name`.

    A clean re-import, not `importlib.reload`. The workbench (adk web with
    reload_agents) watches the same files from its own thread and evicts
    `stage.*` from sys.modules when one changes; an import that races that
    eviction dies with a KeyError from deep inside importlib. So: pop first,
    import, and if the watcher pulled the rug mid-import, simply try again.
    `stage.door` is never popped here — it holds the call that is on the line.
    """
    import time as _t

    last: Exception | None = None
    for _ in range(tries):
        for n in FRESH:
            sys.modules.pop(n, None)
        try:
            mods = {n: importlib.import_module(n) for n in reversed(FRESH)}
            return mods[name]
        except KeyError as exc:                       # the watcher's eviction, mid-import
            last = exc
            _t.sleep(0.05)
    raise last or ImportError(name)


def fresh_all(tries: int = 4) -> dict:
    """All five, imported together, as one consistent generation."""
    import time as _t

    last: Exception | None = None
    for _ in range(tries):
        for n in FRESH:
            sys.modules.pop(n, None)
        try:
            return {n: importlib.import_module(n) for n in reversed(FRESH)}
        except KeyError as exc:
            last = exc
            _t.sleep(0.05)
    raise last or ImportError("stage")


def _strip_comments(src: str) -> str:
    out = []
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        out.append(line.split("  #")[0] if "  #" in line else line)
    return "\n".join(out)


def read(counters: dict[str, Any]) -> dict[str, Any]:
    """One look at the learner's code plus the counters. Never raises — a
    syntax error keeps the last good answer and reports the error alongside."""
    global _last_good
    try:
        mods = fresh_all()                          # one consistent generation of stage.*
        wire, stalls, agent = mods["stage.wire"], mods["stage.stalls"], mods["stage.agent"]
        memory = importlib.import_module("stage.memory")

        up = _strip_comments(inspect.getsource(wire.upstream))
        down = _strip_comments(inspect.getsource(wire.downstream))
        order = _strip_comments(inspect.getsource(stalls.order_snack))
        engine = memory.engine_named_in_env()
        last = counters.get("last_call") or {}

        code = {
            "model": agent.MODEL,
            "model_live": "live" in agent.MODEL,
            "belt": "send_realtime" in up,
            "interrupted": "interrupted" in down,
            "receipt": "order_taken(" in order,
            "tower": bool(engine),
        }
        lit = {
            1: code["model_live"] and counters.get("workbench_calls", 0) > 0,
            2: code["belt"] and last.get("chunks", 0) > 0,
            3: code["interrupted"] and last.get("interrupts", 0) > 0,
            4: code["receipt"] and last.get("order_ms") is not None and last["order_ms"] < 500,
            5: code["tower"] and counters.get("calls_filed", 0) > 0
               and counters.get("facts_recalled", 0) > 0,
        }
        lit[6] = all(lit[i] for i in range(1, 6))
        out = {"code": code, "lit": {str(k): v for k, v in lit.items()},
               "last_call": last, "workbench_calls": counters.get("workbench_calls", 0),
               "calls_filed": counters.get("calls_filed", 0),
               "facts_recalled": counters.get("facts_recalled", 0),
               "store": counters.get("store", ""), "error": None}
        _last_good = out
        return out
    except Exception as exc:                                # noqa: BLE001
        logger.warning("progress could not read the code: %s", exc)
        base = dict(_last_good or {"code": {}, "lit": {}, "last_call": {}})
        base["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return base
