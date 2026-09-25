"use client";
import { CLOSING } from "@/lib/chapters";
import type { SaveFile } from "@/lib/save";

const STAMPS = [
  ["grove", "01 · CONTROL"], ["buildyard", "02 · DECOMPOSE"], ["market", "03 · COORDINATE"],
  ["archive", "04 · REMEMBER"], ["nightmarket", "05 · LIVE"],
];

/** The Familiar Passport, full: five stamps, the season's meta-progression paid off. */
export default function Passport({ save, silence, onClose }: { save: SaveFile; silence: string; onClose: () => void }) {
  return (
    <div className="passport" data-shot="passport">
      <div className="glass card">
        <div className="eyebrow">FAMILIAR PASSPORT · FULL</div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14, marginTop: 12 }}>
          {save.portrait && <img src={save.portrait} alt={save.name} style={{ width: 64, height: 64, borderRadius: "50%", objectFit: "cover", border: "3px solid var(--gold)", boxShadow: "0 6px 16px rgba(185,138,46,.3)" }} />}
          <div style={{ textAlign: "left" }}>
            <div className="serif" style={{ fontSize: 24 }}>{save.name}</div>
            <div className="mono" style={{ fontSize: 10.5, color: "var(--sub)" }}>✦ {save.sparks} · five districts · {silence} silence tonight</div>
          </div>
        </div>
        <div className="stamps">
          {STAMPS.map(([z, k], i) => (
            <div className="stamp" key={z}>
              <img src={`/world/zones/${z}.jpg`} alt={k} />
              <span className="k">{k}</span>
              {save.stamps[i] && <span className="seal">✦</span>}
            </div>
          ))}
        </div>
        <div className="serif" style={{ fontSize: 17, margin: "6px 0 14px" }}>“{CLOSING}”</div>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <button className="rune on" onClick={() => window.print()}>⬇ keep it</button>
          <button className="rune" onClick={onClose}>back to the stage</button>
        </div>
      </div>
    </div>
  );
}
