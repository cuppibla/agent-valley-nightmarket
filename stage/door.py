"""The door — one function stands in front of every tool call.

Three things a door can do, and chapter 4 names them: **observe** (log it and
let it through — return None), **block** (return a dict; the tool never runs
and that dict is what Nix hears back), **rewrite** (edit `args`, return None).

The door is also how the stage lights up. `before_tool_callback` fires the
instant a tool is dispatched — before the tool returns, before the model
speaks again — so the lanterns recolour and the stall card appears the
moment Nix decides, not the moment she finishes. Everything the page learns
mid-call travels through `tell_page`.

The other half of this file is the call registry: the stalls need to find the
belt of the call that is on the line, so the one that is cooking can call out
on it when the food is ready.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

log = logging.getLogger("nightmarket.door")

# Self-study: flip this and order something. The door answers for the stalls,
# and Nix explains in character — the tool never runs.
CLOSED = False


class Call:
    """One call on the line: its belt, the things the page should hear, and
    the clocks the chapter panels show."""

    def __init__(self, queue) -> None:
        self.queue = queue                                 # the belt — LiveRequestQueue
        self.events: asyncio.Queue = asyncio.Queue()       # door verdicts, receipts, clocks → the page
        self.started = time.monotonic()
        self.clocks: dict[str, Any] = {}
        self.tools_in_flight: dict[str, float] = {}
        self.tool_since_audio = False                      # a tool ran since her last audio chunk


_current: Optional[Call] = None


def open_call(queue) -> Call:
    global _current
    _current = Call(queue)
    return _current


def close_call() -> None:
    global _current
    _current = None


def current() -> Optional[Call]:
    return _current


def tell_page(kind: str, **data: Any) -> None:
    """Something for the page — if a call is on the line. From the workbench
    (adk web) there is no page, and that is fine."""
    c = _current
    if c is not None:
        c.events.put_nowait({"type": kind, **data})


async def at_the_door(tool: BaseTool, args: dict[str, Any],
                      tool_context: ToolContext) -> Optional[dict]:
    """Every tool call, before it runs. observe · block · rewrite."""
    log.info("at the door · %s(%s)", tool.name, ", ".join(f"{k}={v!r}" for k, v in args.items()))
    if CLOSED and tool.name == "order_snack":
        tell_page("tool", tool=tool.name, args=dict(args), status="blocked",
                  reason="the stalls are closed")
        return {"status": "closed",
                "reason": "The stalls have closed for the night. Let the visitor down softly."}

    c = _current
    if c is not None:
        c.tools_in_flight[tool.name] = time.monotonic()
        # the silence clock starts here: from the moment she decides until her
        # next word — however long the tool keeps her waiting
        c.clocks["_tool_dispatched_at"] = time.monotonic()
    tell_page("tool", tool=tool.name, args=dict(args), status="ok")
    if tool.name == "light_lanterns":
        tell_page("lanterns", color=str(args.get("color", "")).lower())
    return None                                            # observe only — the tool runs


async def after_the_door(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext,
                         tool_response: dict) -> Optional[dict]:
    """Every tool call, after it returned — one clock: how long her voice waited."""
    c = _current
    if c is None:
        return None
    t0 = c.tools_in_flight.pop(tool.name, None)
    if t0 is not None:
        ms = int((time.monotonic() - t0) * 1000)
        c.clocks["tool_ms"] = ms
        c.clocks["tool"] = tool.name
        if tool.name == "order_snack":
            c.clocks["order_ms"] = ms                  # chapter 4's number
        tell_page("clock", tool=tool.name, tool_ms=ms)
    return None
