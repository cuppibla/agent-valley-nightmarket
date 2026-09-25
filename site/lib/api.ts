// Where the process is. Same origin when the page is served by it (the normal
// case); NEXT_PUBLIC_STAGE_ORIGIN when `npm run dev` runs the page on its own.

export const ORIGIN = process.env.NEXT_PUBLIC_STAGE_ORIGIN || "";

export const wsUrl = (sid: string) => {
  const base = ORIGIN || (typeof window !== "undefined" ? window.location.origin : "");
  return base.replace(/^http/, "ws") + `/ws?sid=${encodeURIComponent(sid)}`;
};

export type Progress = {
  code: { model?: string; model_live?: boolean; belt?: boolean; interrupted?: boolean; receipt?: boolean; tower?: boolean };
  lit: Record<string, boolean>;
  last_call: Record<string, number | string>;
  workbench_calls?: number; calls_filed?: number; facts_recalled?: number;
  store?: string; error: string | null;
};

export async function getProgress(): Promise<Progress | null> {
  try {
    const r = await fetch(`${ORIGIN}/api/progress`, { cache: "no-store" });
    return r.ok ? r.json() : null;
  } catch { return null; }
}

export type CodeFile = { path: string; symbol?: string; span?: number[]; content: string;
  validation: { valid: boolean; message: string; line?: number | null } };

export async function readCode(path: string, symbol?: string): Promise<CodeFile> {
  const r = await fetch(`${ORIGIN}/api/code?path=${encodeURIComponent(path)}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ""}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} from /api/code`);
  return r.json();
}

export async function writeCode(path: string, content: string, symbol?: string): Promise<CodeFile> {
  const r = await fetch(`${ORIGIN}/api/code`, { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ path, content, symbol }) });
  if (!r.ok) throw new Error(`${r.status} from /api/code`);
  return r.json();
}

export type Tower = {
  engine: string; store: string; week4: string;
  build: { state: "idle" | "building" | "done" | "error"; log: string };
};

export async function getTower(): Promise<Tower> {
  const r = await fetch(`${ORIGIN}/api/tower`, { cache: "no-store" });
  return r.json();
}

export async function setTower(action: "week4" | "local" | "build" | "clear" | "paste", value?: string): Promise<Tower> {
  const r = await fetch(`${ORIGIN}/api/tower`, { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ action, value }) });
  return r.json();
}

export async function readEnv(): Promise<{ AGENT_ENGINE: string; store: string }> {
  const r = await fetch(`${ORIGIN}/api/env`, { cache: "no-store" });
  return r.json();
}

export async function writeEnv(engine: string): Promise<{ AGENT_ENGINE: string; store: string }> {
  const r = await fetch(`${ORIGIN}/api/env`, { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ AGENT_ENGINE: engine }) });
  return r.json();
}
