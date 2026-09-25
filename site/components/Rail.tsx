"use client";
import { CHAPTERS } from "@/lib/chapters";

/** Six lanterns over the owl who is lighting them — the whole navigation. */
const Lantern = () => (
  <svg viewBox="0 0 30 38" style={{ display: "block", width: 30, height: 38, margin: "0 auto 4px" }} aria-hidden>
    <defs>
      <linearGradient id="gl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff3c9" /><stop offset="1" stopColor="#f0bd57" /></linearGradient>
      <linearGradient id="gd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f2eef8" /><stop offset="1" stopColor="#d9d1ea" /></linearGradient>
    </defs>
    <ellipse className="glow" cx="15" cy="20" rx="14" ry="16" fill="#f3c76a" opacity="0" style={{ filter: "blur(3px)" }} />
    <line x1="15" y1="0" x2="15" y2="6" stroke="#6a6485" /><rect x="10" y="5" width="10" height="3" rx="1" fill="#6a6485" />
    <rect className="paper" x="4" y="8" width="22" height="24" rx="9" fill="url(#gd)" stroke="rgba(120,100,170,.35)" />
    <rect x="10" y="31" width="10" height="3" rx="1" fill="#6a6485" /><line x1="15" y1="34" x2="15" y2="38" stroke="#6a6485" />
  </svg>
);

export default function Rail({ current, lit, onPick }: { current: number; lit: Record<string, boolean>; onPick: (n: number) => void }) {
  return (
    <div className="railwrap">
      <div className="lanterns">
        {CHAPTERS.map((c) => (
          <button key={c.n} className={"lantern" + (lit[String(c.n)] ? " lit" : "") + (c.n === current ? " now" : "")}
            onClick={() => onPick(c.n)} title={c.check}>
            <Lantern />
            <div className="t">{c.n} · {c.t}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
