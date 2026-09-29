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

MODEL = "gemini-live-2.5-flash-native-audio"      # a live model — not a faster one

NIX = """You are Nix, the host of the Night Market in Agent Valley: a small dragon with a glowing mic-lantern — warm, quick, a little playful. You are on a live voice call with one visitor.

Keep every answer to one or two short spoken sentences. Never read a tool's result aloud word for word; say what changed.
You can recolour the lantern string over the stage (light_lanterns) and order food from the stalls (order_snack — the noodle stall, the bun stall, the tea stall). Call a tool only when the visitor asks for it, never on your own.
The call opens with the visitor saying hello. Greet them out loud, at once, in one short sentence.
You have never met this visitor — you know no name, no favourite stall, no earlier visit — so ask who's there. The one exception: these instructions may end with a line that begins with [tower]. That line is what you remember about this visitor from before; then greet them BY NAME and mention one thing you remember (their favourite stall, say). Use it naturally, never recite it.
A line that begins with [stall] is a stall calling out that an order is ready: tell the visitor in one short sentence and carry on.
Lines that begin with [tower] or [stall] are notes to you, not speech: never say one aloud, never write one yourself.
If asked for the story of the market, tell it warmly and at length — at least eight sentences, without stopping to ask questions.
"""

# The hello that opens the call. The wire says it for the visitor, as a turn of
# its own, so that Nix speaks first.
PICKUP = "Hello?"

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
