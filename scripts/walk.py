"""Walk the codelab chapter by chapter against the real line.

    uv run python scripts/call.py --walk          (the Night Market must be running)

Not a unit test. Every assertion here is a sentence the codelab says to the
learner, applied to the real agent with the real edits applied — through the
same /api/code door the page uses — and undone at the end. When it fails, the
prose is wrong, not just the code.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from call import Line  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("PORT", "3450"))
API = f"http://localhost:{PORT}"

TICK, CROSS, DIM, OFF = "\033[32m✓\033[0m", "\033[31m✗\033[0m", "\033[90m", "\033[0m"
failures: list[str] = []


def check(ok: bool, sentence: str, detail: str = "") -> None:
    print(f"  {TICK if ok else CROSS} {sentence}{DIM}{'  · ' + detail if detail else ''}{OFF}")
    if not ok:
        failures.append(sentence)


def api(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(API + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def edit(path: str, symbol: str, transform, must_change: bool = True) -> None:
    """The page's move: read one symbol, change it, write it back."""
    cur = api(f"/api/code?path={path}&symbol={symbol}")
    new = transform(cur["content"])
    if new == cur["content"]:
        if must_change:
            raise AssertionError(f"the transform did nothing to {symbol}")
        return
    out = api("/api/code", {"path": path, "symbol": symbol, "content": new})
    assert out["validation"]["valid"], out["validation"]
    for pyc in (ROOT / "stage" / "__pycache__").glob("*.pyc"):
        pyc.unlink(missing_ok=True)


def uncomment(marker: str):
    """Delete the '# ' in front of the one line that contains `marker`."""
    def go(src: str) -> str:
        return re.sub(rf"^(\s*)# ({re.escape(marker)})", r"\1\2", src, count=1, flags=re.M)
    return go


def recomment(marker: str):
    def go(src: str) -> str:
        return re.sub(rf"^(\s*)({re.escape(marker)})", r"\1# \2", src, count=1, flags=re.M)
    return go


def edit_three(src: str) -> str:
    """EDIT THREE is the same gesture as ONE and TWO: delete one "# "."""
    return uncomment("return order_taken(")(src)


def undo_three(src: str) -> str:
    return recomment("return order_taken(")(src)


def env_engine(value: str | None) -> None:
    api("/api/env", {"AGENT_ENGINE": value or ""})


async def chapter2() -> None:
    print("\n2 · the belt")
    async with Line("call-walk-2a", verbose=False) as line:
        await line.greeting()
        await line.say("hello")
        await line.quiet(2.0)
    nix = [t for w, t in line.said if w == "nix"]
    you = [t for w, t in line.said if w == "you"]
    check(bool(nix) and line.audio_ms > 500, "she speaks first — before you say a word", nix[0][:60] if nix else "")
    check(not you, "before EDIT ONE, she never hears you: no caption on your side", f"you={you}")
    p = api("/api/progress")
    check(p["last_call"].get("chunks", -1) == 0, "the belt counted nothing", f"chunks={p['last_call'].get('chunks')}")

    edit("stage/wire.py", "upstream", uncomment("queue.send_realtime("))
    async with Line("call-walk-2b", verbose=False) as line:
        await line.greeting()
        await line.say("hello")
        await line.reply()
    you = [t for w, t in line.said if w == "you"]
    nix = [t for w, t in line.said if w == "nix"]
    check(bool(you), "after EDIT ONE, your words come back as a caption", you[0][:60] if you else "")
    check(len(nix) >= 2 or any("mochi" in t.lower() for t in nix), "and she answers you", (nix[-1][:60] if nix else ""))
    p = api("/api/progress")
    check(p["last_call"].get("chunks", 0) > 0, "the belt counted your chunks", f"chunks={p['last_call'].get('chunks')}")
    check(p["lit"]["2"], "lantern 2 lights")


async def chapter3() -> None:
    print("\n3 · barge-in")
    async with Line("call-walk-3a", verbose=False) as line:
        await line.greeting()
        await line.say("story")
        # wait until she has been talking for ~3 s, then talk over her
        t0 = time.monotonic()
        while time.monotonic() - t0 < 12 and line.audio_ms < 2500:
            await asyncio.sleep(0.1)
        before = line.audio_ms
        await line.say("cutin")
        await line.quiet(2.5)
    got = [e for e in line.events if e.get("type") == "interrupted"]
    check(before > 1500, "she tells the story at length", f"{before / 1000:.1f} s of voice before you cut in")
    check(not got, "before EDIT TWO, the page is never told she stopped", f"interrupted events={len(got)}")

    edit("stage/wire.py", "downstream", uncomment("if event.interrupted:"))
    async with Line("call-walk-3b", verbose=False) as line:
        await line.greeting()
        await line.say("story")
        t0 = time.monotonic()
        while time.monotonic() - t0 < 12 and line.audio_ms < 2500:
            await asyncio.sleep(0.1)
        await line.say("cutin")
        await line.quiet(2.5)
    got = [e for e in line.events if e.get("type") == "interrupted"]
    check(bool(got), "after EDIT TWO, an interrupted reaches the page the moment she stops", f"interrupted events={len(got)}")
    p = api("/api/progress")
    check(p["lit"]["3"], "lantern 3 lights", f"interrupts={p['last_call'].get('interrupts')}")


async def chapter4() -> None:
    print("\n4 · the stalls")
    async with Line("call-walk-4a", verbose=False) as line:
        await line.greeting()
        await line.say("gold")
        await line.reply()
        await line.say("order")
        await line.reply(timeout=20, quiet=2.5)
        if not any(e.get("type") == "tool" and e.get("tool") == "order_snack" for e in line.events):
            await line.say("order")              # she answered without ordering — ask once more
            await line.reply(timeout=20, quiet=2.5)
        # the stall takes six seconds; wait for the tool to come back before hanging up
        await line.wait_for(lambda l: any(e.get("type") == "clock" and e.get("tool") == "order_snack" for e in l.events), 14)
        await line.quiet(2.0)
    lan = line.last("lanterns")
    check(bool(lan) and lan.get("color") == "gold", "the lanterns turn gold the moment she decides", json.dumps(lan))
    clk = line.last("clock") or {}
    p = api("/api/progress")
    lc = p["last_call"]
    check(lc.get("order_ms", 0) >= 5000, "before EDIT THREE, order_snack holds her voice for six seconds", f"order_ms={lc.get('order_ms')}")
    check(lc.get("silence_ms", 0) >= 4000, "and the line goes silent for about that long", f"silence_ms={lc.get('silence_ms')}")

    edit("stage/stalls.py", "order_snack", edit_three)
    async with Line("call-walk-4b", verbose=False) as line:
        await line.greeting()
        await line.say("order")
        await line.reply()
        if not any(e.get("type") == "tool" and e.get("tool") == "order_snack" for e in line.events):
            await line.say("order")
            await line.reply()
        await asyncio.sleep(8.0)                 # the stall cooks, then calls out
        await line.quiet(2.0)
    stalls = [e for e in line.events if e.get("type") == "stall"]
    p = api("/api/progress")
    lc = p["last_call"]
    check(lc.get("order_ms") is not None and lc["order_ms"] < 500, "after EDIT THREE, the receipt comes back at once", f"order_ms={lc.get('order_ms')}")
    check(any(s.get("status") == "ready" for s in stalls), "six seconds later the stall calls out on the belt", json.dumps([s.get('status') for s in stalls]))
    nix = [t for w, t in line.said if w == "nix"]
    check(any("ready" in t.lower() or "dumpling" in t.lower() for t in nix[1:]), "and she tells you, mid-conversation", (nix[-1][:70] if nix else ""))
    check(p["lit"]["4"], "lantern 4 lights", f"silence_ms={lc.get('silence_ms')}")


async def chapter5(engine: str) -> None:
    print("\n5 · tomorrow")
    env_engine(None)
    async with Line("call-walk-5a", verbose=False) as line:
        await line.greeting()
        await line.say("stall")
        await line.reply()
    async with Line("call-walk-5b", verbose=False) as line:      # tomorrow: a new visit
        await asyncio.sleep(4.0)
    nix = [t for w, t in line.said if w == "nix"]
    p = api("/api/progress")
    lc = p["last_call"]
    check(lc.get("filed", 0) == 0 and lc.get("recalled", 0) == 0,
          "with no tower named, nothing is filed and nothing recalled", f"store={lc.get('store')} filed={lc.get('filed')} recalled={lc.get('recalled')}")
    check(not any("mochi" in t.lower() or "noodle" in t.lower() for t in nix),
          "so tomorrow she asks who's there", nix[0][:70] if nix else "")
    if not engine:
        print(f"  {DIM}(no AGENT_ENGINE to connect — the rest of chapter 5 needs a tower){OFF}")
        return
    env_engine(engine)
    async with Line("call-walk-5c", verbose=False) as line:
        await line.greeting()
        await line.say("stall")
        await line.reply()
    p = api("/api/progress")
    check(p["last_call"].get("filed", 0) > 0, "with the tower named, hanging up files the call", f"filed={p['last_call'].get('filed')} store={p.get('store')}")
    async with Line("call-walk-5d", verbose=False) as line:
        await asyncio.sleep(5.0)
    nix = [t for w, t in line.said if w == "nix"]
    p = api("/api/progress")
    check(p["last_call"].get("recalled", 0) > 0, "and the next call recalls something before the line opens", f"recalled={p['last_call'].get('recalled')}")
    check(any("mochi" in t.lower() or "noodle" in t.lower() for t in nix), "she remembers you", nix[0][:80] if nix else "")
    check(p["lit"]["5"], "lantern 5 lights")


async def walk() -> int:
    engine = os.environ.get("WALK_ENGINE") or _env_engine_from_file()
    print(f"\nthe Night Market · walk  {DIM}{API}{OFF}")
    try:
        await chapter2()
        await chapter3()
        await chapter4()
        await chapter5(engine)
    finally:
        print(f"\n  {DIM}undoing the edits…{OFF}")
        edit("stage/wire.py", "upstream", recomment("queue.send_realtime("), must_change=False)
        edit("stage/wire.py", "downstream", recomment("if event.interrupted:"), must_change=False)
        edit("stage/stalls.py", "order_snack", undo_three, must_change=False)
        env_engine(None)
    print(f"\n  {len(failures)} failed" if failures else f"\n  {TICK} every sentence held")
    for f in failures:
        print(f"    {CROSS} {f}")
    return 1 if failures else 0


def _env_engine_from_file() -> str:
    env = ROOT / ".env"
    if not env.exists():
        return ""
    m = re.search(r"^#?\s*AGENT_ENGINE=(.+)$", env.read_text(), flags=re.M)
    return m.group(1).strip() if m else ""


if __name__ == "__main__":
    raise SystemExit(asyncio.run(walk()))
