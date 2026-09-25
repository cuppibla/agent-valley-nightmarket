"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { getTower, readCode, setTower, writeCode, type CodeFile, type Tower } from "@/lib/api";

/** One symbol of one file, in the page. The page never holds a copy of your
 *  code: it shows the file, saves it back through /api/code (syntax-checked),
 *  and says exactly when the save takes effect — on your next call. */

type SaveState = "saved" | "unsaved" | "saving" | "invalid";

export function SymbolEditor({ path, symbol, readOnly, marker, fix, onSaved }: {
  path: string; symbol: string; readOnly?: boolean; marker?: string;
  fix?: (src: string) => string; onSaved?: () => void;
}) {
  const [file, setFile] = useState<CodeFile | null>(null);
  const [code, setCode] = useState("");
  const [state, setState] = useState<SaveState>("saved");
  const [err, setErr] = useState("");
  const [onDisk, setOnDisk] = useState<string | null>(null);
  const [savedHere, setSavedHere] = useState(false);     // a save made on this page, this visit
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const known = useRef({ code: "", original: "" });

  const load = useCallback(async () => {
    try {
      const f = await readCode(path, symbol);
      known.current = { code: f.content, original: f.content };
      setFile(f); setCode(f.content); setOnDisk(null); setState("saved"); setErr("");
    } catch (e) { setErr((e as Error).message); }
  }, [path, symbol]);

  useEffect(() => { load(); }, [load]);

  // the file can change under the page — a line typed in your own editor, or
  // the walk. Every few seconds, and whenever the tab comes back: if the disk
  // moved and you have no unsaved edits, show the file as it is now.
  useEffect(() => {
    const poll = async () => {
      try {
        const f = await readCode(path, symbol);
        const { code: c, original: o } = known.current;
        if (f.content === o) return;
        if (c === o) { known.current = { code: f.content, original: f.content }; setFile(f); setCode(f.content); setState("saved"); }
        else setOnDisk(f.content);
      } catch { /* the process is away; the chip says so elsewhere */ }
    };
    const id = setInterval(poll, 4000);
    window.addEventListener("focus", poll);
    return () => { clearInterval(id); window.removeEventListener("focus", poll); };
  }, [path, symbol]);

  const save = async (content: string) => {
    setState("saving");
    try {
      const f = await writeCode(path, content, symbol);
      setFile(f);
      if (f.validation.valid) { known.current = { code: content, original: content }; setState("saved"); setSavedHere(true); onSaved?.(); }
      else setState("invalid");
    } catch (e) { setErr((e as Error).message); setState("invalid"); }
  };

  const onChange = (v: string) => {
    setCode(v); known.current.code = v; setState("unsaved");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => save(v), 700);
  };

  const applyFix = () => {
    if (!fix) return;
    const fixed = fix(code);
    if (fixed === code) return;
    setCode(fixed); known.current.code = fixed;
    if (timer.current) clearTimeout(timer.current);
    save(fixed);
  };

  const lines = code.split("\n");
  const markerLine = marker ? lines.findIndex((l) => l.includes(marker)) + 1 : 0;
  const isDone = fix ? fix(code) === code : false;       // the edit is already in the text
  const chip = readOnly ? <span className="pill" style={{ background: "rgba(255,255,255,.7)", color: "var(--sub)" }}>read only</span>
    : state === "saved" && savedHere && file?.validation.valid
      ? <span className="pill pass">saved · lands on your next call</span>
    : state === "saved"
      ? <span className="pill" style={{ background: "rgba(255,255,255,.7)", color: "var(--sub)" }}>as on disk</span>
      : state === "invalid" ? <span className="pill" style={{ background: "var(--rose)", color: "#fff" }}>not saved · {file?.validation.message || err}</span>
      : state === "saving" ? <span className="pill" style={{ background: "rgba(255,255,255,.7)", color: "var(--sub)" }}>saving…</span>
      : <span className="pill" style={{ background: "rgba(255,255,255,.7)", color: "var(--sub)" }}>unsaved</span>;

  return (
    <div className="editor">
      <div className="head">
        <span>{path} · <b>{symbol}</b>{markerLine > 0 && !readOnly && !isDone && <span style={{ color: "#2f8f6c" }}> · delete the “# ” on line {markerLine}</span>}</span>
        <span style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {onDisk !== null && (
            <button className="pill" style={{ background: "rgba(230,192,105,.25)", color: "var(--gold-deep)", border: "1px solid var(--gold)" }}
              onClick={() => { known.current = { code: onDisk, original: onDisk }; setCode(onDisk); setOnDisk(null); setState("saved"); }}>
              changed on disk · reload
            </button>
          )}
          {chip}
        </span>
      </div>
      {err && !file ? <div className="ln" style={{ color: "var(--rose)", padding: 12 }}>{err}</div> : (
        <div className="body">
          <pre aria-hidden>
            {lines.map((l, i) => {
              const t = l.trimStart();
              const comment = t.startsWith("#");
              // green = delete the "# " at the start of this line · violet = the 👉 notes
              const uncomment = comment && (t.includes("queue.send_realtime") || t.includes("event.interrupted") || t.includes("return order_taken("));
              const cls = uncomment ? "next" : comment ? "hint" : "";
              return <div key={i} className={"ln " + cls}><span className="no">{i + 1}</span><span>{l || " "}</span></div>;
            })}
          </pre>
          <textarea value={code} onChange={(e) => onChange(e.target.value)} readOnly={readOnly} spellCheck={false}
            rows={lines.length} aria-label={`${path} · ${symbol}`} />
        </div>
      )}
      {fix && !readOnly && (
        <div className="foot">
          {isDone ? (
            <span style={{ color: "#2f8f6c" }}>✓ the edit is in. Now 📞 Hang up and 📞 Call again — it lands on the next call.</span>
          ) : (
            <><span>Stuck? </span><button className="copy" onClick={applyFix}>apply the edit for me</button><span> — then read what changed before you call again.</span></>
          )}
        </div>
      )}
    </div>
  );
}

/** Chapter 5's box: name the tower. Three buttons and a paste field, and the
 *  market re-reads .env on the next call. */
export function EnvEditor({ onSaved }: { onSaved?: () => void }) {
  const [t, setT] = useState<Tower | null>(null);
  const [paste, setPaste] = useState("");
  const [busy, setBusy] = useState<string>("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    try { const x = await getTower(); setT(x); return x; } catch { return null; }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  // while a tower is being built, follow its log
  useEffect(() => {
    if (t?.build.state !== "building") return;
    const id = setInterval(async () => {
      const x = await refresh();
      if (x && x.build.state !== "building") { clearInterval(id); onSaved?.(); }
    }, 2000);
    return () => clearInterval(id);
  }, [t?.build.state, refresh, onSaved]);

  const act = async (action: "week4" | "local" | "build" | "clear" | "paste", value?: string) => {
    setBusy(action);
    try { setT(await setTower(action, value)); onSaved?.(); } finally { setBusy(""); }
  };
  const onPaste = (v: string) => {
    setPaste(v);
    if (timer.current) clearTimeout(timer.current);
    if (v.trim().startsWith("projects/")) timer.current = setTimeout(() => act("paste", v.trim()), 900);
  };

  const engine = t?.engine || "";
  const named = Boolean(engine);
  const label = !named ? "no tower named"
    : engine === "local" ? "local tower · forgets when the market closes"
    : `Memory Bank · …/${engine.split("/").slice(-1)[0]}`;
  const building = t?.build.state === "building";

  return (
    <div className="editor">
      <div className="head">
        <span>.env · <b>AGENT_ENGINE</b></span>
        <span className={"pill" + (named ? " pass" : "")} style={named ? {} : { background: "rgba(255,255,255,.7)", color: "var(--sub)" }}>{label}</span>
      </div>
      <div className="tower">
        <div className="opts">
          <button className="rune" disabled={!t?.week4 || busy !== ""} onClick={() => act("week4")}
            title={t?.week4 ? t.week4 : "no ~/agent-valley-archive/.env with an AGENT_ENGINE on this machine"}>
            🗼 week four's tower{t?.week4 ? "" : " · not found"}
          </button>
          <button className="rune" disabled={busy !== "" || building} onClick={() => act("build")}>
            {building ? "⏳ building…" : "🏗 build a tower · about a minute"}
          </button>
          <button className="rune" disabled={busy !== ""} onClick={() => act("local")}>
            💭 local tower · forgets when the market closes
          </button>
          {named && <button className="rune" disabled={busy !== ""} onClick={() => act("clear")}>✕ un-name it</button>}
        </div>
        <div className="paste">
          <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>or paste a resource name:</span>
          <input className="mono" value={paste} onChange={(e) => onPaste(e.target.value)} spellCheck={false}
            placeholder="projects/…/locations/us-central1/reasoningEngines/…" />
        </div>
        {t?.build.log && (
          <pre className="log">{t.build.log.split("\n").slice(-8).join("\n")}</pre>
        )}
        {t?.build.state === "error" && (
          <div className="mono" style={{ fontSize: 11, color: "var(--rose)" }}>
            the tower could not be built. If it says PERMISSION_DENIED or 403, your machine's credentials are not on this project:
            run <code>gcloud auth application-default login</code> and try again — or use the local tower for now.
          </div>
        )}
      </div>
    </div>
  );
}
