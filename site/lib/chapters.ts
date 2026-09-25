// The six lanterns. Each chapter is two lines — what you do, what the market
// does — plus the exact sentences to say (with a copy button), the one edit,
// and one check. The stage teaches by being driven; the codelab carries depth.

export type Chapter = {
  n: number;
  t: string;
  pill: string;
  you: string;                 // what you do — one line
  say?: string[];              // the exact sentence(s) to say to Nix, in order
  market: string;              // what the market does, before the edit
  marketAfter?: string;        // … after it
  file?: string; symbol?: string;
  env?: boolean;               // chapter 5: the editor is the tower box
  marker?: string;             // the line to change (the editor names its number)
  fix?: (src: string) => string;
  check: string;
  table?: string[][];
};

const uncomment = (marker: string) => (src: string) =>
  src.replace(new RegExp(`^(\\s*)# (${marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "m"), "$1$2");

export const CHAPTERS: Chapter[] = [
  { n: 1, t: "the line", pill: "READ ONLY",
    you: "Click 🔬 workbench (top right), pick stage, press the green phone icon, allow the mic, and say:",
    say: ["hi Nix, it's Mochi. what's good tonight?"],
    market: "Nix answers before you finish — with zero frontend. The stage is still dark.",
    file: "stage/agent.py", symbol: "root_agent",
    check: "one call in stage.db from the workbench" },

  { n: 2, t: "the belt", pill: "EDIT ONE",
    you: "📞 Call. She speaks first. Then say:",
    say: ["hi Nix, it's Mochi. what's good tonight?"],
    market: "She waits, and waits. Your voice reaches the belt and dies there ✕. Delete the “# ” on the green line, hang up, call again, say it again.",
    marketAfter: "She hears you and answers by name. Packets ride the belt and her voice comes back.",
    file: "stage/wire.py", symbol: "upstream", marker: "queue.send_realtime(",
    fix: uncomment("queue.send_realtime("),
    check: "chunks rode the belt on the last call" },

  { n: 3, t: "barge-in", pill: "EDIT TWO",
    you: "Ask for the story. About three seconds in, talk over her:",
    say: ["Nix, tell me the whole story of the night market, from the beginning.", "wait, Nix, hold on. which stall has dumplings?"],
    market: "She keeps going for a couple of seconds. The model stopped — your speaker didn't. Delete the “# ” on the green line, hang up, call again, do it again.",
    marketAfter: "She stops mid-word.",
    file: "stage/wire.py", symbol: "downstream", marker: "if event.interrupted:",
    fix: uncomment("if event.interrupted:"),
    check: "an interrupted reached the page on the last call" },

  { n: 4, t: "the stalls", pill: "EDIT THREE",
    you: "On the line, say the first line, then the second:",
    say: ["make the lanterns gold, please.", "order me dumplings from the noodle stall."],
    market: "Lanterns turn gold at once. Then six seconds of silence — she is waiting on the stall. Delete the “# ” on the green line, hang up, call again, order again.",
    marketAfter: "“Dumplings are on!” at once. Six seconds later, mid-chat: “ready!”",
    file: "stage/stalls.py", symbol: "order_snack", marker: "return order_taken(",
    fix: uncomment("return order_taken("),
    check: "the last order returned in under half a second" },

  { n: 5, t: "tomorrow", pill: "CONNECT THE TOWER",
    you: "Say the line. 📞 Hang up. 🗓 tomorrow. 📞 Call.",
    say: ["my favourite stall is the noodle stall, and my name is Mochi. remember that."],
    market: "“Welcome to the Night Market! Who's out there?” She forgot you. Name a tower below, then say it again, hang up, tomorrow, call.",
    marketAfter: "“Welcome back, Mochi — the noodle stall again?”",
    env: true,
    check: "a call was filed, and something was recalled at the next connect" },

  { n: 6, t: "last call", pill: "THE FIFTH STAMP",
    you: "Nothing. Five lanterns are lit.",
    market: "The fifth stamp. Your passport is full.",
    check: "five lanterns",
    table: [["turn-based", "live"], ["one request, one reply", "one open line, two loops"],
      ["await reply", "async for event"], ["send a message", "send_realtime · send_content"],
      ["a tool returns the result", "a tool returns a receipt"],
      ["read memory every turn", "recall at call · file at hang-up"]] },
];

export const CLOSING = "Never make her wait on your code.";
