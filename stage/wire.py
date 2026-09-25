"""The wire — one call on the line, from 📞 to hang-up.

    you ──▶ upstream ──▶ the belt ──▶ run_live ⇄ Gemini Live
    you ◀── downstream ◀──────────────────┘

Two loops, one open line, and neither loop ever waits for the other. That is
what full-duplex means in Python: `asyncio.wait({up, down})` in `open_line`.

Two edits live here, each one line:

    EDIT ONE   chapter 2   `upstream`     your mic goes on the belt
    EDIT TWO   chapter 3   `downstream`   she stopped — tell the page
"""

from __future__ import annotations

import asyncio
import json
import time

from google.adk.agents import LiveRequestQueue
from google.adk.runners import Runner
from google.genai import types

from stage import door, memory
from stage.agent import LIVE, NIX, root_agent

APP = "stage"


# ── you → her ────────────────────────────────────────────────────────────────
async def upstream(ws, queue: LiveRequestQueue) -> None:
    """You → her. Every mic chunk, forever, even silence."""
    while True:
        msg = await ws.receive()
        if msg.get("type") == "websocket.disconnect":
            return
        raw = msg.get("bytes")
        if not raw:
            if control(msg, queue) == "hangup":
                return
            continue
        # 👉 EDIT ONE — chapter 2.
        #    Right now your microphone audio arrives here and is thrown away, so
        #    Nix never hears you. Fix: delete the "# " on the next line. It puts
        #    each audio chunk on the queue that feeds the model.
        # queue.send_realtime(types.Blob(data=raw, mime_type="audio/pcm;rate=16000"))


def control(msg: dict, queue: LiveRequestQueue) -> str | None:
    """The page's other messages: a typed line (a turn, not a stream), the
    clocks it measured on its side, and hang-up."""
    try:
        m = json.loads(msg.get("text") or "{}")
    except ValueError:
        return None
    kind = m.get("type")
    if kind == "text" and m.get("text"):
        queue.send_content(types.Content(role="user", parts=[types.Part(text=m["text"])]))
    elif kind == "clock":
        call = door.current()
        if call is not None:
            call.clocks.update({k: v for k, v in m.items() if k != "type"})
    return kind


# ── her → you ────────────────────────────────────────────────────────────────
async def downstream(ws, runner: Runner, queue: LiveRequestQueue,
                     user_id: str, session_id: str) -> None:
    """Her → you. Not one reply — a stream of events, as long as the line is open."""
    async for event in runner.run_live(user_id=user_id, session_id=session_id,
                                       live_request_queue=queue, run_config=LIVE):
        await observe(ws, event)
        for part in parts(event):
            if part.inline_data and part.inline_data.data:
                await ws.send_bytes(part.inline_data.data)        # her voice, 24 kHz
        # 👉 EDIT TWO — chapter 3.
        #    When you talk over her, the model stops at once and sends an event
        #    with interrupted=True. But the page keeps playing the audio it has
        #    already received. Fix: delete the "# " on the next line. It tells the
        #    page to stop playing right away.
        # if event.interrupted: await ws.send_json({"type": "interrupted"})


def parts(event) -> list:
    return list((event.content.parts if event.content else None) or [])


async def observe(ws, event) -> None:
    """Captions and clocks. Nothing the learner edits."""
    call = door.current()
    now = time.monotonic()
    it, ot = event.input_transcription, event.output_transcription
    if it and it.text:
        await ws.send_json({"type": "caption", "who": "you", "text": it.text,
                            "final": bool(it.finished)})
        if call is not None and it.finished:
            call.clocks["_you_done_at"] = now
    if ot and ot.text:
        await ws.send_json({"type": "caption", "who": "nix", "text": ot.text,
                            "final": bool(ot.finished)})
    if call is None:
        return
    if any(p.inline_data and p.inline_data.data for p in parts(event)):
        if "first_voice_ms" not in call.clocks:
            call.clocks["first_voice_ms"] = int((now - call.started) * 1000)
            await ws.send_json({"type": "clock", "first_voice_ms": call.clocks["first_voice_ms"]})
        you_done = call.clocks.pop("_you_done_at", None)
        if you_done is not None:
            call.clocks["turn_ms"] = int((now - you_done) * 1000)
            await ws.send_json({"type": "clock", "turn_ms": call.clocks["turn_ms"]})
        # silence: from the moment she decided on a tool until her next word
        dispatched = call.clocks.pop("_tool_dispatched_at", None)
        if dispatched is not None:
            call.clocks["silence_ms"] = int((now - dispatched) * 1000)
            await ws.send_json({"type": "clock", "silence_ms": call.clocks["silence_ms"]})
        call.clocks["_last_audio_at"] = now
    if event.turn_complete:
        await ws.send_json({"type": "turn"})


async def feed(ws, call: door.Call) -> None:
    """The door's verdicts, the stalls' receipts, the clocks → the page."""
    while True:
        await ws.send_json(await call.events.get())


# ── the line ─────────────────────────────────────────────────────────────────
class Belt(LiveRequestQueue):
    """The belt, counting what rides it — so the lantern for chapter 2 lights
    on evidence, not on a text match."""

    def __init__(self) -> None:
        super().__init__()
        self.chunks = 0

    def send_realtime(self, blob) -> None:
        self.chunks += 1
        super().send_realtime(blob)


async def open_line(ws, sessions, mem, user_id: str, session_id: str) -> dict:
    """📞 to hang-up. Returns the call's clocks."""
    sess = await sessions.get_session(app_name=APP, user_id=user_id, session_id=session_id)
    if sess is None:
        await sessions.create_session(app_name=APP, user_id=user_id, session_id=session_id)

    # chapter 5 — recall once, before the line opens. Never mid-call.
    remembered = await memory.recall(mem, user_id)
    agent = root_agent.model_copy(update={"instruction": NIX + remembered}) if remembered else root_agent
    runner = Runner(app_name=APP, agent=agent, session_service=sessions, memory_service=mem)

    queue = Belt()
    call = door.open_call(queue)
    call.clocks["recalled"] = memory.count(remembered)
    await ws.send_json({"type": "clock", "recalled": call.clocks["recalled"]})
    # she speaks first: a discrete turn, before you say a word
    queue.send_content(types.Content(role="user", parts=[types.Part(text="[visitor] picks up the line")]))

    up = asyncio.create_task(upstream(ws, queue), name="upstream")
    down = asyncio.create_task(downstream(ws, runner, queue, user_id, session_id), name="downstream")
    tell = asyncio.create_task(feed(ws, call), name="feed")
    try:
        done, pending = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
        queue.close()                                # let run_live wind down on its own
        for t in done:
            if t.exception():
                raise t.exception()
        for t in pending:
            t.cancel()
    finally:
        tell.cancel()
        call.clocks["chunks"] = queue.chunks
        door.close_call()

    # chapter 5 — file once, after the line closes. Off the live path.
    sess = await sessions.get_session(app_name=APP, user_id=user_id, session_id=session_id)
    try:
        call.clocks["filed"] = await memory.file_call(mem, sess) if sess else 0
    except Exception as exc:                                # noqa: BLE001 — a tower that refuses is chapter 5's lesson, not a dropped line
        call.clocks["filed"] = 0
        call.clocks["filed_error"] = f"{type(exc).__name__}: {exc}"[:200]
        await ws.send_json({"type": "error", "message": "the tower refused the filing · " + call.clocks["filed_error"]})
    return call.clocks
