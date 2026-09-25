"use client";
import { useState } from "react";
import type { Clocks, Status } from "@/lib/useCall";

/** The stage: the art, the lantern string you can recolour, Nix and the captions,
 *  📞 · 🗓 · 🎤 · type, and one number. Nothing here is an explanation. */

const LANTERN_COLORS: Record<string, string> = {
  warm: "#ffd98a", gold: "#f0b83a", rose: "#f19ab6", mint: "#8fe0c4", violet: "#c3a8ff",
};

const fmt = (ms: number | string | undefined) => {
  if (ms === undefined || ms === "") return "—";
  const n = Number(ms);
  if (Number.isNaN(n)) return String(ms);
  return n >= 1000 ? `${(n / 1000).toFixed(1)} s` : `${n} ms`;
};

export default function Stage({
  status, captions, clocks, lanterns, stall, level, chapter, portrait, name, remembered,
  onCall, onHangup, onTomorrow, onType, onMute,
}: {
  status: Status; captions: { you: string; nix: string }; clocks: Clocks; lanterns: string;
  stall: { status: string; item: string } | null; level: number; chapter: number;
  portrait?: string; name: string; remembered: number;
  onCall: () => void; onHangup: () => void; onTomorrow: () => void; onType: (t: string) => void; onMute: (on: boolean) => void;
}) {
  const [text, setText] = useState("");
  const [muted, setMuted] = useState(false);
  const off = status === "off" || status === "connecting";
  const col = LANTERN_COLORS[lanterns] || LANTERN_COLORS.warm;
  const bright = lanterns !== "warm";
  const pose = status === "speaking" ? "speaking" : "listening";

  // the one number each chapter is about
  const num: [string, string, string] =
    chapter <= 1 ? ["first voice", fmt(clocks.first_voice_ms), clocks.first_voice_ms ? "good" : ""] :
    chapter === 2 ? ["on the belt", clocks.chunks !== undefined ? String(clocks.chunks) : (clocks.turn_ms ? "flowing" : "0"), clocks.turn_ms ? "good" : "bad"] :
    chapter === 3 ? ["barge-in", fmt(clocks.barge_ms), clocks.barge_ms === undefined ? "" : Number(clocks.barge_ms) < 600 ? "good" : "bad"] :
    chapter === 4 ? ["silence", clocks.silence_ms === undefined ? "—" : fmt(clocks.silence_ms), clocks.silence_ms === undefined ? "" : Number(clocks.silence_ms) < 800 ? "good" : "bad"] :
    chapter === 5 ? ["remembered", remembered ? `${remembered} fact${remembered > 1 ? "s" : ""}` : "0", remembered ? "good" : "bad"] :
    ["silence tonight", clocks.silence_ms === undefined ? "0" : fmt(clocks.silence_ms), "good"];

  const bars = Array.from({ length: 12 }, (_, i) => Math.max(2, Math.min(22, Math.round(level * 240 * (0.6 + ((i * 7) % 5) / 6)))));

  return (
    <div className="glass" style={{ padding: 14 }}>
      <div className={"stage" + (off ? " off" : "")} data-shot="stage">
        <img src="/world/w5/stage.jpg" alt="the Night Market stage" />
        <svg className="string" viewBox="0 0 520 100" preserveAspectRatio="none" aria-hidden>
          <path d="M0 8 C 130 66, 390 66, 520 8" fill="none" stroke="rgba(90,70,50,.7)" strokeWidth="1.5" />
          {Array.from({ length: 9 }, (_, i) => {
            const t = (i + 0.5) / 9, x = t * 520, y = 8 + (1 - Math.pow(2 * t - 1, 2)) * 44;
            return (
              <g key={i}>
                <circle cx={x} cy={y + 20} r="18" fill={col} opacity={bright ? 0.34 : 0.2} />
                <rect x={x - 9} y={y + 6} width="18" height="24" rx="7" fill={col} stroke="rgba(120,80,30,.35)" opacity=".96" />
                <line x1={x} y1={y} x2={x} y2={y + 6} stroke="rgba(90,70,50,.7)" />
              </g>
            );
          })}
        </svg>
        {off && chapter === 1 && <div className="note"><span>say hello in the workbench first →</span></div>}
        {stall && (
          <div className="card">
            <img src="/world/w5/stall.jpg" alt="the noodle stall" />
            <span>{stall.status === "ready" ? `🍜 ${stall.item} · ready!` : `🍜 ${stall.item} · cooking…`}</span>
          </div>
        )}
      </div>

      <div className="scene">
        <div className={"nix" + (status === "speaking" ? " speaking" : "")}>
          <img src={`/world/w5/nix-${pose}.jpg`} alt="Nix" />
        </div>
        <div className="bubble">
          <span>{captions.nix || (off ? "…" : "listening")}</span>
          <div className={"you" + (captions.you ? "" : " dim")}>
            {portrait && <img src={portrait} alt={name} />}
            <span>{captions.you || (off ? "" : "say something")}</span>
          </div>
        </div>
      </div>

      <div className="controls">
        {off
          ? <button className="rune hot" onClick={onCall} disabled={status === "connecting"}>{status === "connecting" ? "📞 …" : "📞 Call"}</button>
          : <button className="rune hot on" onClick={onHangup}>📞 Hang up</button>}
        <button className="rune" onClick={onTomorrow} title="a new visit, same visitor">🗓 tomorrow</button>
        <button className={"rune" + (muted ? " on" : "")} onClick={() => { setMuted(!muted); onMute(!muted); }} title="mute your mic">🎤</button>
        <div className="meter" title="your mic">{bars.map((h, i) => <i key={i} style={{ height: h }} />)}</div>
        <input placeholder="type to Nix ↵" value={text} onChange={(e) => setText(e.target.value)} disabled={off}
          onKeyDown={(e) => { if (e.key === "Enter" && text.trim()) { onType(text.trim()); setText(""); } }} />
      </div>
      <div><span className={"num " + num[2]}>{num[0]} <b>{num[1]}</b></span></div>
    </div>
  );
}
