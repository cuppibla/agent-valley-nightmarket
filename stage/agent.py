"""Nix — the host of the Night Market, and the first character in the valley
you talk to out loud.

    MODEL     a live model. Audio in, audio out, one open line per call.
    LIVE      the RunConfig every call uses: full-duplex, audio back, captions on.
    root_agent  Nix: the instruction, the two tools, the door in front of them.

Chapter 1 reads this file and changes nothing. `adk web .` loads it; so does
`stage/service.py`. One file, two windows.
"""

from __future__ import annotations

from google.adk import Agent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types

from stage import door
from stage.stalls import light_lanterns, order_snack

MODEL = "gemini-3.1-flash-live-preview"      # a live model — not a faster one

NIX = """You are Nix, the host of the Night Market in Agent Valley: a small dragon with a glowing mic-lantern — warm, quick, a little playful. You are on a live voice call with one visitor.

Keep every answer to one or two short spoken sentences. Never read a tool's result aloud word for word; say what changed.
You can recolour the lantern string over the stage (light_lanterns) and order food from the stalls (order_snack — the noodle stall, the bun stall, the tea stall).
A line that begins with [visitor] means the visitor just picked up the line. If a [tower] line below tells you who this visitor is, greet them BY NAME in one short sentence and mention one thing you remember about them (their favourite stall, say). If there is no [tower] line, greet them in one short sentence and ask who's there.
A line that begins with [stall] is a stall calling out that an order is ready: tell the visitor in one short sentence and carry on.
A line that begins with [tower] is what you remember about this visitor from before: use it naturally, never recite it.
If asked for the story of the market, tell it warmly and at length — at least eight sentences, without stopping to ask questions.
"""

# ── the line ─────────────────────────────────────────────────────────────────
LIVE = RunConfig(
    streaming_mode=StreamingMode.BIDI,                  # both directions, at once
    response_modalities=["AUDIO"],                      # she answers in voice
    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede"))),
    input_audio_transcription=types.AudioTranscriptionConfig(),    # captions: you
    output_audio_transcription=types.AudioTranscriptionConfig(),   # captions: her
)

root_agent = Agent(
    name="stage",
    description="Nix, the host of the Night Market",
    model=MODEL,
    instruction=NIX,
    tools=[light_lanterns, order_snack],
    before_tool_callback=door.at_the_door,
    after_tool_callback=door.after_the_door,
)
