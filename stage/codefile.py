"""The in-page editor's back end: read and write ONE top-level symbol of one
of the files the lab asks you to edit. Python is syntax-checked before it is
written, and the page never holds a copy of your code — it shows the file.

Borrowed from VibeStudio's workbench (`server/api/code.py`), trimmed to what
the Night Market needs.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# path → what the codelab says about it
FILES = {
    "stage/agent.py": "Nix: the model, the instruction, the tools, the door (read only)",
    "stage/wire.py": "the two loops — EDIT ONE in upstream, EDIT TWO in downstream",
    "stage/stalls.py": "the two tools — EDIT THREE in order_snack",
    "stage/memory.py": "recall at connect · file at hang-up (read only)",
}


def resolve(path: str) -> Path:
    if path not in FILES:
        raise KeyError(f"{path} is not open to the editor")
    return ROOT / path


def validate(path: str, content: str) -> dict:
    if path.endswith(".py"):
        try:
            ast.parse(content, filename=path)
        except SyntaxError as e:
            return {"valid": False, "message": f"SyntaxError: {e.msg}", "line": e.lineno}
        return {"valid": True, "message": "Python syntax OK"}
    return {"valid": True, "message": "OK"}


def symbol_span(content: str, symbol: str) -> tuple[int, int] | None:
    """1-based inclusive line span of a top-level `def symbol` or `symbol = …`,
    extended over the indented comment lines right after the body — the 👉
    lines a learner is meant to see."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None
    lines = content.splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            end = node.end_lineno or node.lineno
            while end < len(lines) and lines[end].strip().startswith("#") and lines[end][:1] in (" ", "\t"):
                end += 1
            return start, end
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == symbol
                                                for t in node.targets):
            return node.lineno, node.end_lineno or node.lineno
    return None


def read(path: str, symbol: str | None = None) -> dict:
    p = resolve(path)
    content = p.read_text()
    v = validate(path, content)
    if not symbol:
        return {"path": path, "content": content, "validation": v}
    span = symbol_span(content, symbol)
    if span is None:
        raise KeyError(f"{symbol} is not a top-level symbol of {path}")
    lines = content.splitlines(keepends=True)
    return {"path": path, "symbol": symbol, "span": list(span),
            "content": "".join(lines[span[0] - 1:span[1]]), "validation": v}


def write(path: str, content: str, symbol: str | None = None) -> dict:
    """Write the whole file, or splice `content` over that one symbol. The
    result carries the syntax check; nothing invalid reaches the disk."""
    p = resolve(path)
    if symbol:
        current = p.read_text()
        span = symbol_span(current, symbol)
        if span is None:
            return {"path": path, "symbol": symbol, "content": content,
                    "validation": {"valid": False, "message": f"{symbol} is no longer in the file on disk"}}
        lines = current.splitlines(keepends=True)
        new = content if content.endswith("\n") else content + "\n"
        whole = "".join(lines[:span[0] - 1]) + new + "".join(lines[span[1]:])
        v = validate(path, whole)
        if not v["valid"]:
            return {"path": path, "symbol": symbol, "content": content, "validation": v}
        if symbol_span(whole, symbol) is None:
            return {"path": path, "symbol": symbol, "content": content,
                    "validation": {"valid": False, "message": f"the edit removed `{symbol}` — keep its name"}}
        _write(p, whole)
        return read(path, symbol)
    v = validate(path, content)
    if not v["valid"]:
        return {"path": path, "content": content, "validation": v}
    _write(p, content)
    return read(path)


def _write(p: Path, content: str) -> None:
    """Write, and drop the cached bytecode: Python keys a .pyc on the source's
    mtime in whole seconds, so two saves inside one second could otherwise be
    served stale by the reload."""
    p.write_text(content)
    for pyc in (p.parent / "__pycache__").glob(f"{p.stem}.*.pyc"):
        try:
            pyc.unlink()
        except OSError:
            pass
