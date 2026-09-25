"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Chapter from "@/components/Chapter";
import FamiliarPicker from "@/components/FamiliarPicker";
import Passport from "@/components/Passport";
import Rail from "@/components/Rail";
import SaveChip from "@/components/SaveChip";
import Stage from "@/components/Stage";
import Wire from "@/components/Wire";
import Workbench from "@/components/Workbench";
import { getProgress, type Progress } from "@/lib/api";
import { getSave, updateSave, type SaveFile } from "@/lib/save";
import { useCall } from "@/lib/useCall";

/** The Night Market — one page, fixed shape.
 *
 * Left, the stage: you talk to Nix, she talks back, the lanterns and the
 * stalls do what she asks. Right, the wire (the architecture, alive while the
 * line is open) and the chapter: two lines, one edit, one check.
 *
 * Six lanterns, and each lights when its call proves it — the process reads
 * your code and the counters it kept, never a checklist. Nothing restarts: an
 * edit lands on your next 📞 Call.
 */

const SID_KEY = "a101.w5.sid";
const CH_KEY = "a101.w5.ch";
const newSid = () => "call-" + Math.random().toString(36).slice(2, 10);

export default function NightMarket() {
  const [save, setSave] = useState<SaveFile | null | undefined>(undefined);
  const [chapter, setChapter] = useState(1);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [sid, setSid] = useState("");
  const [drawer, setDrawer] = useState(false);
  const [passport, setPassport] = useState(false);
  const [down, setDown] = useState(false);
  const fails = useRef(0);

  const onProgress = useCallback((p: Progress) => { setProgress(p); setDown(false); fails.current = 0; }, []);
  const line = useCall(sid, onProgress);

  const refresh = useCallback(async () => {
    const p = await getProgress();
    if (p) { setProgress(p); setDown(false); fails.current = 0; }
    else if (++fails.current >= 2) setDown(true);
  }, []);

  useEffect(() => {
    // ?as=Mochi seats a familiar without the picker — for the capture rig
    // and for anyone who already has one from an earlier week's save.
    const who = new URLSearchParams(window.location.search).get("as");
    if (who && !getSave()?.name) {
      const src = "/world/icons/species/cat.jpg";
      updateSave({ name: who, portrait: src, origin: src, sparks: 30, outfit: [], inventory: [], stamps: [true, true, true, true, false] });
    }
    setSave(getSave());
    let s = "";
    try { s = localStorage.getItem(SID_KEY) || ""; } catch { /* private mode */ }
    if (!s) { s = newSid(); try { localStorage.setItem(SID_KEY, s); } catch { /* ignore */ } }
    setSid(s);
    // ?ch=N opens a chapter directly (the capture rig, and deep links from the codelab)
    const want = parseInt(new URLSearchParams(window.location.search).get("ch") || "", 10);
    try {
      const c = want >= 1 && want <= 6 ? want : parseInt(localStorage.getItem(CH_KEY) || "1", 10);
      if (c >= 1 && c <= 6) setChapter(c);
    } catch { if (want >= 1 && want <= 6) setChapter(want); }
    refresh();
    const id = setInterval(refresh, 3000);
    const back = () => { if (document.visibilityState === "visible") refresh(); };
    document.addEventListener("visibilitychange", back);
    return () => { clearInterval(id); document.removeEventListener("visibilitychange", back); };
  }, [refresh]);

  const go = (n: number) => { setChapter(n); try { localStorage.setItem(CH_KEY, String(n)); } catch { /* ignore */ } };

  const tomorrow = () => {
    if (line.status !== "off") line.hangup();
    const s = newSid();
    try { localStorage.setItem(SID_KEY, s); } catch { /* ignore */ }
    setSid(s);
  };

  // the fifth stamp: yours once lantern 5 is lit
  useEffect(() => {
    if (save && progress?.lit?.["5"] && !save.stamps[4]) {
      const stamps = [...save.stamps]; stamps[4] = true;
      setSave(updateSave({ stamps, sparks: save.sparks + 3 }));
    }
  }, [progress, save]);

  if (save === undefined || !sid) return null;
  if (!save?.name) return <FamiliarPicker eyebrow="THE NIGHT MARKET · 05 LIVE" title="Who's in the front row tonight?" cta="✦ take a seat" onDone={() => setSave(getSave())} />;

  const status = down ? "the market is closed" : line.status === "speaking" ? "she's talking" : line.status === "on" ? "on the line" : line.status === "connecting" ? "picking up" : "off the line";
  const dot = down ? "#6b6394" : line.status === "off" ? "var(--faint)" : line.status === "speaking" ? "var(--rose)" : "var(--mint)";
  const remembered = Number(line.clocks.recalled || 0);
  const silence = line.clocks.silence_ms === undefined ? "0 s" : `${(Number(line.clocks.silence_ms) / 1000).toFixed(1)} s`;

  return (
    <div className="wrap" style={{ maxWidth: 1340, paddingBottom: 30 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 14, gap: 16 }}>
        <div>
          <div className="eyebrow"><Link href="/" style={{ color: "inherit" }}>AGENT VALLEY</Link> · 05 · LIVE</div>
          <h1 className="serif" style={{ fontWeight: 500, fontSize: 30, margin: "4px 0 0" }}>The Night Market</h1>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span className="mono" style={{ fontSize: 11, color: "var(--sub)", display: "inline-flex", alignItems: "center", gap: 7 }}>
            <i style={{ width: 8, height: 8, borderRadius: "50%", background: dot, display: "inline-block" }} />{status}
          </span>
          <SaveChip />
          <button className={"rune" + (drawer ? " on" : "")} onClick={() => setDrawer(!drawer)}>🔬 workbench</button>
        </div>
      </div>

      <Rail current={chapter} lit={progress?.lit || {}} onPick={go} />

      <div className="main" style={{ display: "grid", gridTemplateColumns: "520px 1fr", gap: 16, alignItems: "start" }}>
        <Stage status={line.status} captions={line.captions} clocks={line.clocks} lanterns={line.lanterns}
          stall={line.stall} level={line.level} chapter={chapter} portrait={save.portrait} name={save.name} remembered={remembered}
          onCall={line.call} onHangup={line.hangup} onTomorrow={tomorrow} onType={line.type} onMute={line.mute} />
        <div style={{ display: "grid", gap: 16 }}>
          <Wire chapter={chapter} progress={progress} status={line.status} lanternsLit={line.lanterns !== "warm"} />
          <Chapter n={chapter} progress={progress} onGo={go} onSaved={refresh} onPassport={() => setPassport(true)} />
        </div>
      </div>

      {line.lastEvent?.type === "error" && (
        <div className="mono" style={{ marginTop: 12, fontSize: 12, color: "var(--rose)" }}>{line.lastEvent.message}</div>
      )}

      <Workbench open={drawer} onClose={() => setDrawer(false)} />
      {passport && <Passport save={save} silence={silence} onClose={() => setPassport(false)} />}
    </div>
  );
}
