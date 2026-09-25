"""The headless learner — a mouth for the capture rig, and the lab's walk.

Live audio cannot be click-tested, so this pushes real spoken fixtures
(`scripts/fixtures/*.pcm`, 16 kHz mono PCM) into the line the way the page's
mic does, and prints what came back: captions, events, clocks. Every check in
`walk()` is a sentence the codelab says to the learner.

    uv run python scripts/call.py hello                 # one fixture, print everything
    uv run python scripts/call.py story cutin@3.0       # say story; 3 s in, talk over her
    uv run python scripts/call.py gold order            # chapter 4
    uv run python scripts/call.py --sid call-x stall    # chapter 5, then again with --sid call-y
    uv run python scripts/call.py --walk                # the whole ladder, edits applied and undone

Needs the Night Market running:  bash valley.sh   (or PORT=… for another port)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "scripts" / "fixtures"
PORT = int(os.environ.get("PORT", "3450"))
CHUNK = 3200                      # 100 ms of 16 kHz PCM16
SILENCE = bytes(CHUNK)


def fixture(name: str) -> bytes:
    return (FIX / f"{name}.pcm").read_bytes()


class Line:
    """One call. Sends fixtures with real-time pacing, keeps silence flowing,
    collects everything the server says."""

    def __init__(self, sid: str, verbose: bool = True) -> None:
        self.sid, self.verbose = sid, verbose
        self.said: list[tuple[str, str]] = []          # (who, text) finals
        self.events: list[dict] = []
        self.audio_ms = 0.0
        self.audio_at: list[float] = []                 # arrival times of her audio chunks
        self.t0 = time.monotonic()
        self.speaking_since: float | None = None
        self._partial: dict[str, str] = {}

    async def __aenter__(self):
        self.ws = await websockets.connect(f"ws://localhost:{PORT}/ws?sid={self.sid}",
                                           max_size=None)
        self.reader = asyncio.create_task(self._read())
        self.mic = asyncio.create_task(self._silence())
        return self

    async def __aexit__(self, *_):
        await self.hangup()

    async def hangup(self):
        self.mic.cancel()
        try:
            await self.ws.send(json.dumps({"type": "hangup"}))
            await asyncio.wait_for(self.reader, 20)
        except Exception:                                    # noqa: BLE001
            self.reader.cancel()
        try:
            await self.ws.close()
        except Exception:                                    # noqa: BLE001
            pass

    def log(self, *a):
        if self.verbose:
            print(f"  {time.monotonic() - self.t0:6.2f}s ", *a)

    async def _silence(self):
        while True:
            await self.ws.send(SILENCE)
            await asyncio.sleep(0.1)

    async def _read(self):
        async for msg in self.ws:
            now = time.monotonic()
            if isinstance(msg, (bytes, bytearray)):
                self.audio_ms += len(msg) / 2 / 24000 * 1000
                self.audio_at.append(now)
                continue
            m = json.loads(msg)
            self.events.append(m)
            kind = m.get("type")
            if kind == "caption":
                # ADK sends the pieces as they arrive, then the whole line
                # once more with final=True — the final replaces, never appends.
                who = m["who"]
                if m.get("final"):
                    text = m["text"].strip() or self._partial.pop(who, "").strip()
                    self._partial.pop(who, None)
                    self.said.append((who, text))
                    self.log(f"{who:>4} · {text}")
                else:
                    self._partial[who] = self._partial.get(who, "") + m["text"]
            elif kind == "progress":
                self.log("progress ·", json.dumps(m.get("lit")), "last_call", json.dumps(m.get("last_call")))
            elif kind in ("clock", "tool", "lanterns", "stall", "interrupted", "turn", "error"):
                self.log(kind, "·", json.dumps({k: v for k, v in m.items() if k != "type"}))

    async def say(self, name: str):
        """Push one fixture at real-time pace (the silence task keeps running
        between chunks, which is fine — the model hears a steady stream)."""
        data = fixture(name)
        self.log(f"you say · {name} ({len(data) / 32000:.1f} s)")
        self.mic.cancel()
        for i in range(0, len(data), CHUNK):
            await self.ws.send(data[i:i + CHUNK])
            await asyncio.sleep(0.1)
        self.mic = asyncio.create_task(self._silence())

    async def type(self, text: str):
        self.log(f"you type · {text}")
        await self.ws.send(json.dumps({"type": "text", "text": text}))

    async def quiet(self, seconds: float):
        """Wait until her audio has been quiet for `seconds`, or 25 s."""
        start = time.monotonic()
        while time.monotonic() - start < 25:
            await asyncio.sleep(0.25)
            if self.audio_at and time.monotonic() - self.audio_at[-1] > seconds:
                return
            if not self.audio_at and time.monotonic() - start > 8:
                return

    async def greeting(self, timeout: float = 10) -> bool:
        """She speaks first. Wait for that, then for her to finish."""
        ok = await self.wait_for(lambda l: l.audio_ms > 300, timeout)
        if ok:
            await self.quiet(1.2)
        return ok

    async def reply(self, timeout: float = 15, quiet: float = 1.5) -> bool:
        """Wait for her to answer what you just said: new audio after now,
        then `quiet` seconds of silence. False if she never answered."""
        since = time.monotonic()
        while time.monotonic() - since < timeout:
            await asyncio.sleep(0.2)
            if self.audio_at and self.audio_at[-1] > since:
                await self.quiet(quiet)
                return True
        return False

    def last(self, kind: str) -> dict | None:
        return next((e for e in reversed(self.events) if e.get("type") == kind), None)

    async def wait_for(self, pred, timeout: float = 12) -> bool:
        """Wait until `pred(self)` is true, or give up."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if pred(self):
                return True
            await asyncio.sleep(0.2)
        return False


async def run(sid: str, steps: list[str]):
    async with Line(sid) as line:
        await line.greeting()                        # she speaks first
        for step in steps:
            name, _, delay = step.partition("@")
            if delay:
                await asyncio.sleep(float(delay))
            else:
                await line.quiet(1.2)
            await line.say(name)
        await line.quiet(2.0)
        await asyncio.sleep(1.0)
    print(f"\n  her audio: {line.audio_ms / 1000:.1f} s · captions: {len(line.said)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("steps", nargs="*")
    ap.add_argument("--sid", default=f"call-test-{int(time.time())}")
    ap.add_argument("--walk", action="store_true")
    a = ap.parse_args()
    if a.walk:
        from walk import walk                          # scripts/walk.py
        return asyncio.run(walk())
    asyncio.run(run(a.sid, a.steps or ["hello"]))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    raise SystemExit(main())
