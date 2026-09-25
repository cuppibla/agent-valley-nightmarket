"use client";
import { useState } from "react";
import { CHAPTERS, CLOSING } from "@/lib/chapters";
import type { Progress } from "@/lib/api";
import { EnvEditor, SymbolEditor } from "./Editor";

/** The chapter panel: you · the market · the one edit · one check. */

function Say({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <div className="say">
      <span>“{text}”</span>
      <button className="copy" onClick={async () => {
        try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1200); } catch { /* clipboard blocked */ }
      }}>{done ? "copied ✓" : "copy"}</button>
    </div>
  );
}

export default function Chapter({ n, progress, onGo, onSaved, onPassport }: {
  n: number; progress: Progress | null; onGo: (n: number) => void; onSaved: () => void; onPassport: () => void;
}) {
  const c = CHAPTERS[n - 1];
  const prev = CHAPTERS[n - 2], next = CHAPTERS[n];
  const code = progress?.code || {};
  const edited = n === 2 ? Boolean(code.belt) : n === 3 ? Boolean(code.interrupted) : n === 4 ? Boolean(code.receipt) : n === 5 ? Boolean(code.tower) : false;
  const ok = Boolean(progress?.lit?.[String(n)]);
  const market = edited && c.marketAfter ? c.marketAfter : c.market;

  return (
    <div className="glass chapter" data-shot="chapter">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div><span className="eyebrow">CHAPTER {c.n}</span><div className="serif" style={{ fontSize: 22, marginTop: 2 }}>{c.t}</div></div>
        <span className={"pill " + (n === 6 ? "gold" : "pass")} style={n === 1 ? { background: "rgba(255,255,255,.7)", color: "var(--sub)" } : {}}>{c.pill}</span>
      </div>

      <div className="step">
        <b>you</b>
        <div style={{ display: "grid", gap: 8 }}>
          <span>{c.you}</span>
          {c.say?.map((s) => <Say key={s} text={s} />)}
        </div>
        <b>the market</b>
        <span className="m">{market}</span>
      </div>

      {c.env ? <EnvEditor onSaved={onSaved} />
        : c.file && c.symbol ? <SymbolEditor path={c.file} symbol={c.symbol} readOnly={n === 1} marker={c.marker} fix={c.fix} onSaved={onSaved} />
        : (
          <>
            <table className="table">
              <tbody>{c.table!.map((r, i) => <tr key={i}>{r.map((x, j) => i ? <td key={j}>{x}</td> : <th key={j}>{x}</th>)}</tr>)}</tbody>
            </table>
            <div className="serif" style={{ fontSize: 17, margin: "14px 0 8px" }}>“{CLOSING}”</div>
            <button className="rune on" onClick={onPassport} disabled={!ok} title={ok ? "" : "light all five lanterns first"}>✦ the fifth stamp</button>
          </>
        )}

      <div className={"check" + (ok ? " ok" : "")}><span className="box">{ok ? "✓" : "▢"}</span><span className="txt">{c.check}</span></div>
      {progress?.error && <div className="mono" style={{ fontSize: 11, color: "var(--rose)", marginTop: 6 }}>{progress.error}</div>}

      <div className="nav">
        {prev ? <button className="rune" onClick={() => onGo(prev.n)}>← {prev.n} · {prev.t}</button> : <span />}
        {next ? <button className="rune on" onClick={() => onGo(next.n)}>{next.n} · {next.t} →</button>
          : <button className="rune on" onClick={() => onGo(1)}>back to the line</button>}
      </div>
    </div>
  );
}
