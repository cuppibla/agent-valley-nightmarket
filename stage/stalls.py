"""The stalls — Nix's two abilities.

One is instant. One takes six seconds, and chapter 4 is about what those six
seconds cost her voice. A tool is synchronous to her: she does not speak again
until it returns. Silence in a conversation does not read as loading; it reads
as broken. So the rule for every tool on a live line is **acknowledge, don't
await** — hand back a receipt now, do the work in a task, and when it is done,
drop the result on the belt as a turn of its own.
"""

from __future__ import annotations

import asyncio

from google.adk.tools import ToolContext
from google.genai import types

from stage import door
from stage.state import LANTERNS, ORDERS

COLORS = ("gold", "rose", "mint", "violet", "warm")
STALLS = ("the noodle stall", "the bun stall", "the tea stall")
COOK_S = 6


def light_lanterns(color: str, tool_context: ToolContext) -> dict:
    """Change the colour of the lantern string over the stage. Instant.

    Args:
        color: one of gold, rose, mint, violet, warm.
    """
    color = color.lower().strip()
    if color not in COLORS:
        return {"error": f"the string only does {', '.join(COLORS)}"}
    tool_context.state[LANTERNS] = color
    return {"lanterns": color}


async def cook(stall: str, item: str) -> dict:
    """The stall, cooking. Six seconds, and nothing to do but wait."""
    await asyncio.sleep(COOK_S)
    return {"stall": stall, "item": item, "ready": True}


async def cook_and_call(stall: str, item: str) -> None:
    """Cook in the background. When it is done, call it out on the belt — a
    discrete turn, mid-conversation — so Nix can tell the visitor."""
    await cook(stall, item)
    door.tell_page("stall", status="ready", stall=stall, item=item)
    call = door.current()
    if call is not None:
        call.queue.send_content(types.Content(role="user", parts=[types.Part(
            text=f"[stall] {stall}: the {item} is ready. Tell the visitor in one short sentence.")]))


def order_taken(stall: str, item: str) -> dict:
    """Acknowledge, don't await: start the cooking as a task, hand back a receipt.
    The food comes back later, on the belt — see `cook_and_call`."""
    asyncio.create_task(cook_and_call(stall, item))
    return {"status": "ordered", "eta_s": COOK_S}


async def order_snack(stall: str, item: str, tool_context: ToolContext) -> dict:
    """Order one thing from a stall. The stall cooks it and calls out when it is ready.

    Args:
        stall: which stall — the noodle stall, the bun stall or the tea stall.
        item: what to order, a few words.
    """
    tool_context.state[ORDERS] = list(tool_context.state.get(ORDERS, [])) + [item]
    door.tell_page("stall", status="cooking", stall=stall, item=item)
    # 👉 EDIT THREE — chapter 4.
    #    Right now this function waits 6 seconds for the stall to cook (the last
    #    line below), and Nix cannot say a word until it returns.
    #    Fix: delete the "# " on the next line. The function then returns a
    #    receipt right away and starts the cooking in the background, so the
    #    6-second line under it is never reached.
    # return order_taken(stall, item)
    return await cook(stall, item)                       # waits 6 seconds — silence
