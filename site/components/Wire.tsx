"use client";
import type { Progress } from "@/lib/api";
import type { Status } from "@/lib/useCall";

/** The wire: four boxes in a row, two below. Nodes light as chapters enable
 *  them; packets move while the line is open. No more words than that. */

const N = {
  you:   { x: 14,  y: 30, w: 120, h: 54, l: "🎙 you", s: "mic · 16 kHz" },
  belt:  { x: 176, y: 30, w: 190, h: 54, l: "the belt", s: "LiveRequestQueue" },
  nix:   { x: 408, y: 30, w: 210, h: 54, l: "🐉 Nix", s: "run_live · Gemini Live" },
  spk:   { x: 660, y: 30, w: 110, h: 54, l: "🔊 you", s: "speaker · 24 kHz" },
  door:  { x: 408, y: 126, w: 210, h: 50, l: "🏮 the door", s: "before_tool_callback · tools" },
  tower: { x: 660, y: 126, w: 110, h: 50, l: "🗼 tower", s: "Memory Bank" },
} as const;
const E = {
  "you-belt": "M134 57 L176 57", "belt-nix": "M366 57 L408 57", "nix-spk": "M618 57 L660 57",
  "nix-door": "M513 84 L513 126", "door-belt": "M408 151 L271 151 L271 84",
  "tower-nix": "M700 126 L700 100 L600 100 L600 84", "nix-tower": "M740 126 L740 108 L612 108 L612 84",
} as const;
const P = {
  up:    { d: "M40 57 L176 57 L366 57 L500 57", cls: "pk", dur: "2.2s" },
  drop:  { d: "M40 57 L176 57 L200 57", cls: "pk", dur: "1.5s" },
  down:  { d: "M520 70 L618 70 L700 70", cls: "pk down", dur: "1.8s" },
  door:  { d: "M513 84 L513 130", cls: "pk text", dur: "1.2s" },
  stall: { d: "M408 151 L271 151 L271 84", cls: "pk text", dur: "2.2s" },
  mem:   { d: "M700 126 L700 100 L600 100 L600 84", cls: "pk mem", dur: "2s" },
} as const;

export default function Wire({ chapter, progress, status, lanternsLit }: {
  chapter: number; progress: Progress | null; status: Status; lanternsLit: boolean;
}) {
  const code = progress?.code || {};
  const on = status !== "off" && status !== "connecting";
  const belt = Boolean(code.belt);
  const lit = new Set<string>();
  if (chapter >= 1) lit.add("nix");
  if (chapter >= 2 && on) { lit.add("you"); lit.add("belt"); }
  if (chapter >= 2 && on && belt) lit.add("spk");
  if (chapter >= 4) lit.add("door");
  if (chapter >= 5 && code.tower) lit.add("tower");
  const edges = new Set<string>();
  if (lit.has("you")) edges.add("you-belt");
  if (lit.has("spk")) { edges.add("belt-nix"); edges.add("nix-spk"); }
  if (lit.has("door")) { edges.add("nix-door"); if (code.receipt) edges.add("door-belt"); }
  if (lit.has("tower")) { edges.add("tower-nix"); edges.add("nix-tower"); }
  const packets: (keyof typeof P)[] = [];
  if (on && chapter >= 2) packets.push(belt ? "up" : "drop");
  if (on && belt) packets.push("down");
  if (on && chapter >= 4 && lanternsLit) packets.push("door");
  if (on && chapter >= 4 && code.receipt) packets.push("stall");
  if (on && chapter >= 5 && code.tower) packets.push("mem");
  const hot = chapter === 3 && !code.interrupted ? "spk" : "";

  const legend =
    chapter === 1 ? "the workbench talks to the same Nix. no stage yet." :
    chapter === 2 ? (belt ? "one line: send_realtime. the belt is one timeline, both ways." : "before: ✕ nothing puts your mic on the belt.") :
    chapter === 3 ? (code.interrupted ? "interrupted → the page empties the speaker. two clocks, one rule." : "an interrupted event arrives — but her queued voice keeps playing in your speaker.") :
    chapter === 4 ? (code.receipt ? "a receipt now; the food rides the belt back later. acknowledge, don't await." : "the door lights the lanterns at once — but Nix is frozen ❄ while order_snack awaits.") :
    chapter === 5 ? (code.tower ? "recall once when you call · file once when you hang up. never mid-call." : "no tower named: the call stays a record in stage.db, and nobody reads it.") :
    "one line · one belt · one door · one tower.";

  return (
    <div className="glass wire" data-shot="wire">
      <svg viewBox="0 0 780 200" role="img" aria-label="you, the belt, Nix on Gemini Live, back to you; the door for tools; the tower for memory">
        <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#8a6bff" /></marker></defs>
        {Object.entries(E).map(([k, d]) => (
          <path key={k} d={d} className={"edge" + (edges.has(k) ? " lit" : "") + (k.includes("tower") ? " mem" : "")} markerEnd="url(#a)" />
        ))}
        {Object.entries(N).map(([k, n]) => (
          <g key={k}>
            <rect x={n.x} y={n.y} width={n.w} height={n.h} rx="12" className={"node" + (lit.has(k) ? " lit" : "") + (hot === k ? " hot" : "")} />
            <text x={n.x + n.w / 2} y={n.y + 23} textAnchor="middle" className={"nl" + (lit.has(k) ? " lit" : "")}>{n.l}</text>
            <text x={n.x + n.w / 2} y={n.y + 41} textAnchor="middle" className="ns">{n.s}</text>
          </g>
        ))}
        {packets.includes("drop") && <text x="205" y="22" className="nl" style={{ fill: "#e58aa8", fontWeight: 700 }}>✕ dies here</text>}
        {chapter === 4 && !code.receipt && on && <text x="528" y="110" className="nl" style={{ fill: "#e58aa8", fontWeight: 700 }}>❄ frozen while a stall cooks</text>}
        {packets.map((k) => Array.from({ length: 3 }, (_, i) => (
          <circle key={`${k}${i}`} r="4" className={P[k].cls}>
            <animateMotion dur={P[k].dur} repeatCount="indefinite" begin={`${(i * 0.7).toFixed(1)}s`} path={P[k].d} />
          </circle>
        )))}
      </svg>
      <div className="lg">{legend}</div>
    </div>
  );
}
