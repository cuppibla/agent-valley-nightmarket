"""What survives the call.

A call leaves a transcript, not a recording — and only if someone files it.
Two moments, and neither is on the live path:

    recall      once, before the line opens    the tower → the instruction
    file_call   once, after the line closes    the transcript → the tower

The tower is the Archive's: Vertex AI Memory Bank, named by AGENT_ENGINE in
`.env`. Until it is named, the store is in-process and forgets with the
process — chapter 5 watches that happen before connecting the real one.

The one gotcha worth a paragraph: a live session keeps its transcripts in
`event.input_transcription` / `event.output_transcription`, **not** in
`content.parts`. Memory Bank's extractor reads parts. Filed as they are, a
whole evening's call looks empty. `transcript_events` turns them into plain
text events first.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from google.adk.events import Event
from google.adk.memory.base_memory_service import BaseMemoryService
from google.genai import types

APP = "stage"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

# Week four's dict. `wait_for_completion` is why the tower is honest: the
# filing blocks until Memory Bank has finished extracting, so the very next
# call can already find it. The in-process store ignores it.
FILING: dict = {"wait_for_completion": True}

QUERY = "who is this visitor, what do they like at the market, what did they order"


def engine_named_in_env() -> str:
    """AGENT_ENGINE as `.env` has it right now — not as it was at start."""
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text().splitlines():
        m = re.match(r"\s*AGENT_ENGINE\s*=\s*(.*)", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return ""


class NoTower(BaseMemoryService):
    """No tower named: the market keeps nothing. Every call is still a record
    in stage.db — floor one, in the Archive's words — but nobody reads it back.
    That is chapter 5's "before", and it is deterministic on purpose."""

    keeps_nothing = True          # read by file_call — an attribute, because the
                                  # service holds one instance across many fresh imports

    async def add_session_to_memory(self, session) -> None:
        return None

    async def add_events_to_memory(self, *, app_name, user_id, events, session_id=None,
                                   custom_metadata=None) -> None:
        return None

    async def search_memory(self, *, app_name, user_id, query):
        from google.adk.memory.base_memory_service import SearchMemoryResponse
        return SearchMemoryResponse()


def tower_service(engine: str) -> BaseMemoryService:
    """The memory service for a tower name — or, with none, one that keeps nothing.

    `AGENT_ENGINE=local` is a tower made of process memory: it files and
    recalls across calls, and forgets when the market closes. Enough to see
    chapter 5 happen without a Google Cloud project; the real tower is Memory
    Bank, and it outlives the process.
    """
    if engine == "local":
        from google.adk.memory import InMemoryMemoryService

        return InMemoryMemoryService()
    if engine:
        from google.adk.memory import VertexAiMemoryBankService

        return VertexAiMemoryBankService(
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("MEMORY_BANK_LOCATION", "us-central1"),
            agent_engine_id=engine.split("/")[-1],
        )
    return NoTower()


# ── at connect ───────────────────────────────────────────────────────────────
async def recall(mem: BaseMemoryService, user_id: str) -> str:
    """Ask the tower once. Returns a line for the instruction, or nothing."""
    try:
        found = await mem.search_memory(app_name=APP, user_id=user_id, query=QUERY)
    except Exception:                                       # noqa: BLE001 — a tower that is down is chapter 5's problem, not the call's
        return ""
    facts = []
    for m in found.memories:
        text = " ".join(p.text for p in (m.content.parts or []) if p.text).strip()
        if text:
            facts.append(text)
    if not facts:
        return ""
    return "\n[tower] What you remember about this visitor: " + " · ".join(facts[:6])


def count(remembered: str) -> int:
    return remembered.count(" · ") + 1 if remembered else 0


# ── at hang-up ───────────────────────────────────────────────────────────────
def transcript_events(session) -> list[Event]:
    """The call as plain text events, in order: you / nix. Wake-ups and stall
    call-outs (the `[…]` lines) are stage directions, not conversation."""
    out: list[Event] = []
    for ev in session.events:
        it, ot = ev.input_transcription, ev.output_transcription
        if it and it.text and it.finished:
            out.append(_said("user", it.text))
        if ot and ot.text and ot.finished:
            out.append(_said("nix", ot.text))
        elif ev.content and ev.author == "user":
            text = " ".join(p.text for p in (ev.content.parts or []) if p.text).strip()
            if text and not text.startswith("["):
                out.append(_said("user", text))
    return out


def _said(who: str, text: str) -> Event:
    return Event(author=who, content=types.Content(
        role="user" if who == "user" else "model", parts=[types.Part(text=text)]))


async def file_call(mem: BaseMemoryService, session) -> int:
    """File the call in the tower. Returns how many lines were filed."""
    events = transcript_events(session)
    if not events or getattr(mem, "keeps_nothing", False):
        return 0
    await mem.add_events_to_memory(app_name=APP, user_id=session.user_id,
                                   session_id=session.id, events=events,
                                   custom_metadata=FILING)
    return len(events)
