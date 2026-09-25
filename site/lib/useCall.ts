"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { wsUrl, type Progress } from "./api";

/** One call on the line, from the page's side.
 *
 * Up: the mic, as 16 kHz PCM16 from an AudioWorklet (public/pcm-processor.js),
 * one binary frame per ~100 ms, and typed lines as json. Down: her voice as
 * 24 kHz PCM16 frames, scheduled back to back on an AudioContext, plus json —
 * captions, the door's verdicts, the stalls' receipts, the clocks.
 *
 * Deliberately NOT here: a local mic-level stop. Chapter 3 is about the two
 * clocks, and the page only empties its speaker when the server says
 * `interrupted` (EDIT TWO). Before that edit, her queued voice plays out —
 * which is the point. The page measures how long that takes.
 */

export type Caption = { who: "you" | "nix"; text: string; final: boolean };
export type Clocks = Record<string, number | string>;
export type Status = "off" | "connecting" | "on" | "speaking" | "down";

export type CallEvent =
  | { type: "caption"; who: "you" | "nix"; text: string; final: boolean }
  | { type: "lanterns"; color: string }
  | { type: "stall"; status: "cooking" | "ready"; stall: string; item: string }
  | { type: "tool"; tool: string; args: Record<string, unknown>; status: string; reason?: string }
  | { type: "clock"; [k: string]: number | string }
  | { type: "interrupted" }
  | { type: "turn" }
  | { type: "progress"; [k: string]: unknown }
  | { type: "error"; message: string };

const BARGE_RMS = 0.02;

export function useCall(sid: string, onProgress?: (p: Progress) => void) {
  const [status, setStatus] = useState<Status>("off");
  const [captions, setCaptions] = useState<{ you: string; nix: string }>({ you: "", nix: "" });
  const [clocks, setClocks] = useState<Clocks>({});
  const [lanterns, setLanterns] = useState<string>("warm");
  const [stall, setStall] = useState<{ status: string; item: string } | null>(null);
  const [level, setLevel] = useState(0);
  const [lastEvent, setLastEvent] = useState<CallEvent | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const ctx = useRef<AudioContext | null>(null);
  const mic = useRef<MediaStream | null>(null);
  const node = useRef<AudioWorkletNode | null>(null);
  const nextStart = useRef(0);
  const sources = useRef<AudioBufferSourceSource[]>([]);
  const speaking = useRef(false);
  const bargeAt = useRef<number | null>(null);      // when your voice rose over hers
  const partial = useRef<{ you: string; nix: string }>({ you: "", nix: "" });
  const muted = useRef(false);

  type AudioBufferSourceSource = AudioBufferSourceNode;

  const send = (obj: Record<string, unknown>) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(obj));
  };

  const stopVoice = useCallback(() => {
    sources.current.forEach((s) => { try { s.stop(); } catch { /* already ended */ } });
    sources.current = [];
    nextStart.current = 0;
    if (speaking.current) {
      speaking.current = false;
      setStatus((s) => (s === "speaking" ? "on" : s));
      if (bargeAt.current !== null) {
        const ms = Math.round(performance.now() - bargeAt.current);
        bargeAt.current = null;
        setClocks((c) => ({ ...c, barge_ms: ms }));
        send({ type: "clock", barge_ms: ms });
      }
    }
  }, []);

  const playVoice = (buf: ArrayBuffer) => {
    const ac = ctx.current; if (!ac) return;
    const int16 = new Int16Array(buf);
    const f32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) f32[i] = int16[i] / 0x8000;
    const ab = ac.createBuffer(1, f32.length, 24000);
    ab.getChannelData(0).set(f32);
    const src = ac.createBufferSource();
    src.buffer = ab; src.connect(ac.destination);
    const now = ac.currentTime;
    if (nextStart.current < now) nextStart.current = now;
    src.start(nextStart.current); nextStart.current += ab.duration;
    sources.current.push(src);
    src.onended = () => {
      sources.current = sources.current.filter((s) => s !== src);
      if (!sources.current.length) {
        speaking.current = false;
        setStatus((s) => (s === "speaking" ? "on" : s));
        if (bargeAt.current !== null) {                 // her queue drained on its own — that IS the before-edit number
          const ms = Math.round(performance.now() - bargeAt.current);
          bargeAt.current = null;
          setClocks((c) => ({ ...c, barge_ms: ms }));
          send({ type: "clock", barge_ms: ms });
        }
      }
    };
    speaking.current = true;
    setStatus("speaking");
  };

  const hangup = useCallback(() => {
    send({ type: "hangup" });
    node.current?.disconnect(); node.current = null;
    mic.current?.getTracks().forEach((t) => t.stop()); mic.current = null;
    stopVoice();
    setTimeout(() => { try { ws.current?.close(); } catch { /* closed */ } ws.current = null; }, 800);
    setStatus("off");
    setStall(null);
  }, [stopVoice]);

  const call = useCallback(async () => {
    if (ws.current) return;
    setStatus("connecting");
    setCaptions({ you: "", nix: "" }); partial.current = { you: "", nix: "" };
    setClocks({}); setStall(null); setLanterns("warm");
    try {
      const ac = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      ctx.current = ac;
      await ac.audioWorklet.addModule("/pcm-processor.js");
      mic.current = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    } catch (e) {
      setStatus("off");
      setLastEvent({ type: "error", message: "the page needs the microphone: " + (e as Error).message });
      return;
    }
    const sock = new WebSocket(wsUrl(sid));
    sock.binaryType = "arraybuffer";
    ws.current = sock;
    sock.onopen = () => {
      setStatus("on");
      const ac = ctx.current!;
      const source = ac.createMediaStreamSource(mic.current!);
      const n = new AudioWorkletNode(ac, "pcm-processor");
      n.port.onmessage = (e) => {
        if (sock.readyState === WebSocket.OPEN && !muted.current) sock.send(e.data.pcm);   // 16 kHz PCM up
        setLevel(e.data.rms);
        // you started talking over her: start the barge-in clock (the page never stops her itself)
        if (e.data.rms >= BARGE_RMS && speaking.current && bargeAt.current === null) bargeAt.current = performance.now();
      };
      source.connect(n);
      node.current = n;
    };
    sock.onclose = () => { ws.current = null; setStatus((s) => (s === "off" ? "off" : "off")); };
    sock.onerror = () => setStatus("down");
    sock.onmessage = (evt) => {
      if (typeof evt.data !== "string") { playVoice(evt.data); return; }
      const m = JSON.parse(evt.data) as CallEvent;
      setLastEvent(m);
      if (m.type === "caption") {
        // ADK sends the pieces as they arrive, then the whole line once more
        // with final=true — the final replaces, never appends.
        const who = m.who;
        if (m.final) {
          const text = (m.text.trim() || partial.current[who]).trim();
          partial.current[who] = "";
          setCaptions((c) => ({ ...c, [who]: text }));
        } else {
          partial.current[who] += m.text;
          const text = partial.current[who];
          setCaptions((c) => ({ ...c, [who]: text }));
        }
      } else if (m.type === "interrupted") stopVoice();
      else if (m.type === "lanterns") setLanterns(m.color || "warm");
      else if (m.type === "stall") setStall({ status: m.status, item: m.item });
      else if (m.type === "clock") setClocks((c) => ({ ...c, ...Object.fromEntries(Object.entries(m).filter(([k]) => k !== "type")) }));
      else if (m.type === "progress") onProgress?.(m as unknown as Progress);
    };
  }, [sid, stopVoice, onProgress]);

  const type = useCallback((text: string) => send({ type: "text", text }), []);
  const mute = useCallback((on: boolean) => { muted.current = on; }, []);

  useEffect(() => () => { hangup(); }, [hangup]);

  return { status, captions, clocks, lanterns, stall, level, lastEvent, call, hangup, type, mute };
}
