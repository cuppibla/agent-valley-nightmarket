"""Build the tower — the Agent Engine instance that hosts your Memory Bank.

If you did week four, you do not need this: paste that lab's AGENT_ENGINE line
into `.env` and Nix shares Vesper's tower. Otherwise, one SDK call. It writes
the resource name into `.env` as AGENT_ENGINE, and the Night Market reads that
file on every call, so there is nothing to restart. About a minute.

    uv run python scripts/make_tower.py

Run it twice and it will not raise a second tower: it looks for the one it
already made, by display name.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import forge  # noqa: E402  — settles project + credentials, same as every surface

NAME = "agent-valley-nightmarket-tower"
ENV = ROOT / ".env"


def remember(resource: str) -> None:
    """AGENT_ENGINE=<full resource name> into .env, replacing any earlier one."""
    text = ENV.read_text() if ENV.exists() else ""
    line = f"AGENT_ENGINE={resource}"
    if re.search(r"^#?\s*AGENT_ENGINE=.*$", text, flags=re.M):
        text = re.sub(r"^#?\s*AGENT_ENGINE=.*$", line, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n\n# the tower — built by scripts/make_tower.py\n{line}\n"
    ENV.write_text(text)


def main() -> int:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("MEMORY_BANK_LOCATION", "us-central1")
    if not project:
        print("\n  ✗ The tower needs a Google Cloud project.\n"
              "      gcloud config set project YOUR_PROJECT_ID\n"
              "      gcloud auth application-default login\n"
              "    Memory Bank is a Vertex AI service; an AI Studio key cannot reach it.\n")
        return 1

    import vertexai
    client = vertexai.Client(project=project, location=location)
    try:
        engine = next((e for e in client.agent_engines.list()
                       if (e.api_resource.display_name or "") == NAME), None)
        if engine is None:
            print(f"\n  building the tower in {project} / {location} — about a minute…")
            engine = client.agent_engines.create(config={"display_name": NAME})
            print("  built.")
        else:
            print("\n  the tower is already standing.")
    except Exception as exc:                               # noqa: BLE001
        msg = f"{type(exc).__name__}: {exc}"
        print(f"\n  ✗ the tower could not be built:\n    {msg[:400]}\n")
        if "billing" in msg.lower():
            print("    Memory Bank needs billing enabled on the project:\n"
                  "      https://console.cloud.google.com/billing\n")
        elif "permission" in msg.lower() or "403" in msg:
            print("    Your account needs the Vertex AI User role on this project,\n"
                  "    and the API switched on:\n"
                  "      gcloud services enable aiplatform.googleapis.com\n")
        return 1

    resource = engine.api_resource.name
    remember(resource)
    print(f"\n  resource: {resource}")
    print("  AGENT_ENGINE written to .env — the next call uses it.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
