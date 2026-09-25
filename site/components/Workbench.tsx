"use client";
import { ORIGIN } from "@/lib/api";

/** adk web, in a drawer. Same stage/ folder, same stage.db — one file, two windows. */
export default function Workbench({ open, onClose }: { open: boolean; onClose: () => void }) {
  const src = `${ORIGIN}/workbench/dev-ui/?app=stage`;
  return (
    <div className={"drawer" + (open ? " open" : "")} aria-hidden={!open}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div>
          <div className="eyebrow" style={{ color: "#b08fe0" }}>🔬 THE WORKBENCH</div>
          <div className="mono" style={{ fontSize: 11, color: "#bdb3dc", marginTop: 4 }}>adk web · same stage/, same stage.db</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <a className="rune" href={src} target="_blank" rel="noreferrer"
            style={{ background: "rgba(255,255,255,.08)", color: "#e8e3f6", borderColor: "rgba(150,120,220,.4)" }}>open in a tab ↗</a>
          <button className="rune" onClick={onClose}
            style={{ background: "rgba(255,255,255,.08)", color: "#e8e3f6", borderColor: "rgba(150,120,220,.4)" }}>✕</button>
        </div>
      </div>
      {open && (
        <iframe src={src} title="adk web" allow="microphone; autoplay"
          style={{ flex: 1, width: "100%", border: "1px solid rgba(150,120,220,.35)", borderRadius: 12, background: "#17142a" }} />
      )}
      <div className="mono" style={{ fontSize: 10.5, color: "#8f85b3", marginTop: 10, lineHeight: 1.5 }}>
        pick <b style={{ color: "#e8e3f6" }}>stage</b>, press the mic, say hello. chapter 1 lives here; every other chapter, on the stage.
      </div>
    </div>
  );
}
