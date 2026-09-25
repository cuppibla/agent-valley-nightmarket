# The Night Market — Agent Valley, week five

Opens after dark. Everything at once, out loud, no second takes.

This is the lab repo for **Agent 101 Live, chapter five: Live**. Nix, the host,
is the first character in the valley you talk to — out loud, and you can cut
her off. Six lanterns, three one-line edits, one tower to connect, and every
lantern lights when a real call proves it.

```
1  the line      a live model, one open connection          read only · the workbench
2  the belt      LiveRequestQueue · send_realtime           EDIT ONE   stage/wire.py   upstream
3  barge-in      the interrupted event · two clocks         EDIT TWO   stage/wire.py   downstream
4  the stalls    a tool holds her voice · acknowledge, don't await   EDIT THREE   stage/stalls.py   order_snack
5  tomorrow      recall at connect · file at hang-up        connect    .env   AGENT_ENGINE
6  last call     the fifth stamp
```

Over the door: *Real-time is a shape, not a speed.*
The sentence the week ends on: **Never make her wait on your code.**

## Run it

```bash
uv sync
cp .env.example .env                   # point at a project, or paste a key
uv run python scripts/preflight.py     # is this machine ready — does the line open?
bash valley.sh                         # one process, one port
```

Open **http://localhost:3450**, press ▶ Start, take a seat, and follow the
lanterns. Everything happens on that page: you talk to Nix, you edit the one
line each chapter is about, and the workbench (adk web) is a drawer on the
same page — same `stage/` folder, same `stage.db`.

Nothing restarts. An edit lands on your **next 📞 Call**; the chip under the
editor says so.

## What is where

```
stage/
  agent.py      Nix: a live model, the instruction, two tools, the door in front of them
  wire.py       the two loops — upstream (EDIT ONE) and downstream (EDIT TWO) — and open_line
  stalls.py     light_lanterns (instant) · order_snack (EDIT THREE) · cook_and_call
  door.py       before_tool_callback: observe · block · rewrite — and how the page hears about it
  memory.py     recall once at connect · file once at hang-up · the transcript gotcha
  state.py      every key the market writes, and how long each one lives
  progress.py   which lanterns are lit: your code, comments stripped, plus the last call's counters
  service.py    one FastAPI: the page · /ws · /api/code · /api/progress · /workbench (adk web, mounted)
scripts/
  preflight.py  am I ready — opens the line for two seconds, prints the lantern bar
  call.py       the headless learner: pushes spoken fixtures into /ws the way the mic does
  walk.py       every sentence the codelab says, applied to the real line, edits done and undone
  edits.py      apply / undo the three edits from a terminal, through the page's own door
  make_tower.py build an Agent Engine for Memory Bank, if you have no week-four tower
site/           the page — Next.js, exported to static files once by valley.sh
```

## The one that keeps everyone honest

```bash
uv run python scripts/call.py --walk
```

Not a unit test: every check is a sentence the codelab says to the learner,
run against the real agent with the real edits applied through `/api/code`
and undone at the end. Chapter 5's second half needs a tower named in `.env`.

## The workbench on its own

```bash
uv run adk web --session_service_uri=sqlite:///stage.db . --allow_origins="*"
```

Same file, same sessions, two surfaces. The page mounts exactly this at
`/workbench`.
