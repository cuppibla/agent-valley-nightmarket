"""Is this machine ready, and which lanterns are lit?

Run it now, and again any time you want the answer to "which edits have I
actually made?" — every line is read from your code, not from a checklist.

    uv run python scripts/preflight.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import forge  # noqa: E402  — settles Vertex-vs-key before anything else

TICK, BOX = "\033[32m✓\033[0m", "\033[90m▢\033[0m"
DIM, OFF = "\033[90m", "\033[0m"


def bar(p: dict) -> list[str]:
    code, lit = p["code"], p["lit"]
    rows = [
        (1, "the line", code.get("model", "?"), "read only · say hello in the workbench"),
        (2, "the belt", "upstream puts your mic on the belt" if code.get("belt")
            else "upstream drops your mic on the floor", "chapter 2 · EDIT ONE"),
        (3, "barge-in", "downstream tells the page she stopped" if code.get("interrupted")
            else "downstream keeps her voice queued", "chapter 3 · EDIT TWO"),
        (4, "the stalls", "order_snack hands back a receipt" if code.get("receipt")
            else "order_snack waits for the stall", "chapter 4 · EDIT THREE"),
        (5, "tomorrow", ".env names a tower" if code.get("tower") else ".env names no tower",
            "chapter 5 · connect"),
    ]
    return [f"  {n}  {TICK if lit.get(str(n)) else BOX} {name:<12}{DIM}· {how:<40}{note}{OFF}"
            for n, name, how, note in rows]


async def live_check(model: str) -> str:
    """Open the line for two seconds. Proves the key can do Live, not just chat."""
    from google import genai
    from google.genai import types

    client = genai.Client()
    config = types.LiveConnectConfig(response_modalities=["AUDIO"],
                                     output_audio_transcription=types.AudioTranscriptionConfig())
    heard = ""
    async with client.aio.live.connect(model=model, config=config) as session:
        await session.send_client_content(turns=types.Content(
            role="user", parts=[types.Part(text="Say the single word: ready.")]))
        try:
            async with asyncio.timeout(12):
                async for msg in session.receive():
                    sc = msg.server_content
                    if sc and sc.output_transcription and sc.output_transcription.text:
                        heard += sc.output_transcription.text
                    if sc and sc.turn_complete:
                        break
        except TimeoutError:
            pass
    return heard.strip()


def why(mode: str) -> str:
    """The likeliest fix for a line that did not open. The error itself is cut
    short — a WebSocket close carries 123 bytes — so this reads the setup."""
    where = os.environ.get("GOOGLE_CLOUD_LOCATION", "")
    if mode == "api-key":
        return ("This lab's live model is a Vertex AI model; an API key cannot reach it.\n"
                "    Take GOOGLE_API_KEY out of .env and point gcloud at a project — see .env.example.")
    if where == "global":
        return ("Vertex serves its live models from regions, not from `global`.\n"
                "    Set GOOGLE_CLOUD_LOCATION=us-central1 in .env.")
    return ("Live needs a model that does audio in and out. Check the model name in\n"
            f"    stage/agent.py and that your project can reach it in {where or 'its region'}.")


def main() -> int:
    print()
    mode = forge.MODE
    if not mode:
        print("  ✗ Not configured. Point gcloud at a project:")
        print("        gcloud config set project YOUR_PROJECT_ID")
        print("    — see .env.example.")
        return 1
    where = os.environ.get("GOOGLE_CLOUD_PROJECT", "?") if mode == "vertex" else "an API key"
    print(f"  talking to Gemini through {DIM}{mode} · {where}{OFF}")

    from stage import agent, memory, progress

    try:
        heard = asyncio.run(live_check(agent.MODEL))
        print(f"  the line opens {DIM}· {agent.MODEL} · she said: {heard[:40] or '(audio only)'}{OFF}")
    except Exception as exc:                               # noqa: BLE001
        print(f"  ✗ the line did not open: {type(exc).__name__}: {exc}"[:240])
        print("    " + why(mode))
        return 1

    engine = memory.engine_named_in_env()
    print(f"  the tower {DIM}· " + (f"reasoningEngines/{engine.split('/')[-1]}" if engine
          else "not named yet — chapter 5 connects it") + OFF)
    built = (ROOT / "site" / "out" / "index.html").exists()
    print(f"  the page {DIM}· " + ("built" if built else "not built yet — bash valley.sh builds it once") + OFF)

    print("\n  the lanterns:\n")
    p = progress.read({"last_call": {}, "workbench_calls": 0, "calls_filed": 0, "facts_recalled": 0})
    for line in bar(p):
        print(line)
    print(f"\n  {DIM}none are lit before you start — each one lights when its call proves it,"
          f" not when the code reads right.{OFF}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
