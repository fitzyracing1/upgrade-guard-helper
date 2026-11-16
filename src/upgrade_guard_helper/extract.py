"""Extract default parameters and config constants ("knobs") from Python and JS.

A knob, as defined by fitzyracing1/knobs, is a default parameter or setting
that can change silently between versions and change how a system behaves.
This module uses the Python ast module and simple regular expressions for JS.
It does not depend on knoblog.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

PYTHON_SUFFIXES = {".py"}
JS_SUFFIXES = {".js", ".mjs", ".cjs", ".ts"}
SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".tox",
    "test",
    "tests",
}


@dataclass(frozen=True)
class Knob:
    """A named default value found in source."""

    name: str
    value: str
    language: str
    path: str


def _literal(node: ast.AST) -> str | None:
    if not isinstance(node, (ast.Constant, ast.Tuple, ast.List, ast.UnaryOp, ast.Dict, ast.Set)):
        return None
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError):
        return None
    text = ast.unparse(node)
    return text if len(text) <= 120 else None


def extract_python(text: str, path: str = "module.py") -> list[Knob]:
    """Collect function/constructor defaults, class attributes, and UPPER constants."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    found: list[Knob] = []

    def add(name: str, value: str) -> None:
        found.append(Knob(name=name, value=value, language="python", path=path))

    def visit(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                visit(node.body, f"{prefix}{node.name}.")
                for stmt in node.body:
                    target = None
                    value_node = None
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        target = stmt.target.id
                        value_node = stmt.value
                    elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                        tgt = stmt.targets[0]
                        if isinstance(tgt, ast.Name):
                            target = tgt.id
                            value_node = stmt.value
                    if target and not target.startswith("_") and value_node is not None:
                        literal = _literal(value_node)
                        if literal is not None:
                            add(f"{prefix}{node.name}.{target}", literal)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") and node.name != "__init__":
                    continue
                args = node.args
                positional = args.posonlyargs + args.args
                pairs = list(
                    zip(positional[len(positional) - len(args.defaults) :], args.defaults)
                )
                for key, default in zip(args.kwonlyargs, args.kw_defaults):
                    if default is not None:
                        pairs.append((key, default))
                if node.name == "__init__" and prefix:
                    fname = prefix[:-1]
                else:
                    fname = f"{prefix}{node.name}"
                for arg, default in pairs:
                    if arg.arg.startswith("_"):
                        continue
                    literal = _literal(default)
                    if literal is not None:
                        add(f"{fname}({arg.arg})", literal)
            elif isinstance(node, ast.AnnAssign) and prefix == "":
                if isinstance(node.target, ast.Name) and node.target.id.isupper() and node.value:
                    literal = _literal(node.value)
                    if literal is not None:
                        add(node.target.id, literal)
            elif isinstance(node, ast.Assign) and prefix == "":
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                    if name.isupper():
                        literal = _literal(node.value)
                        if literal is not None:
                            add(name, literal)

    visit(tree.body, "")
    return found


# JS / TS default parameters and const literals. Intentionally simple regexes.
_JS_LIT = (
    r"(-?\d[\d_.]*(?:e[-+]?\d+)?|true|false|null|undefined|"
    r"'[^'\n]{0,80}'|\"[^\"\n]{0,80}\"|`[^`$\n]{0,80}`)"
)
_JS_FUNC = re.compile(
    rf"(?:function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)|"
    rf"(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*\(([^)]*)\)\s*=>|"
    rf"([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{{)"
)
_JS_PARAM = re.compile(rf"([A-Za-z_$][\w$]*)\s*=\s*{_JS_LIT}")
_JS_CONST = re.compile(
    rf"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*{_JS_LIT}\s*;?\s*(?://.*)?$",
    re.MULTILINE,
)
_JS_OBJ_START = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)?\s*"
    r"((?:[A-Za-z_$][\w$.]*)?(?:[Dd]efaults?|DEFAULTS?|[Cc]onfig|[Oo]ptions)\w*)"
    r"\s*=\s*(?:Object\.freeze\()?\s*\{\s*$"
)
_JS_KV = re.compile(rf"^\s*['\"]?([A-Za-z_$][\w$-]*)['\"]?\s*:\s*{_JS_LIT}\s*,?\s*(?://.*)?$")
_JS_NEST = re.compile(r"^\s*['\"]?([A-Za-z_$][\w$-]*)['\"]?\s*:\s*\{\s*$")


def extract_js(text: str, path: str = "module.js") -> list[Knob]:
    """Collect JS/TS default parameters, config objects, and interesting consts."""
    found: list[Knob] = []

    def add(name: str, value: str) -> None:
        found.append(Knob(name=name, value=value, language="js", path=path))

    for match in _JS_FUNC.finditer(text):
        name = match.group(1) or match.group(3) or match.group(5)
        params = match.group(2) or match.group(4) or match.group(6) or ""
        if not name or name.startswith("_"):
            continue
        for param in _JS_PARAM.finditer(params):
            add(f"{name}({param.group(1)})", param.group(2))

    for match in _JS_CONST.finditer(text):
        ident = match.group(1)
        if ident.isupper() or re.search(
            r"default|timeout|max|min|limit|retr|size|delay", ident, re.I
        ):
            add(ident, match.group(2))

    stack: list[str] = []
    skip = 0
    for line in text.splitlines():
        code = re.sub(r"//.*$", "", line)
        if stack:
            if skip:
                skip += code.count("{") + code.count("[") - code.count("}") - code.count("]")
                continue
            nested = _JS_NEST.match(code)
            if nested:
                stack.append(nested.group(1))
                continue
            kv = _JS_KV.match(code)
            if kv:
                add(".".join(stack + [kv.group(1)]), kv.group(2))
                continue
            opened = code.count("{") + code.count("[") - code.count("}") - code.count("]")
            if opened > 0:
                skip = opened
                continue
            if re.match(r"^\s*[}\]]", code):
                stack.pop()
            continue
        start = _JS_OBJ_START.match(code)
        if start:
            stack = [start.group(1)]

    return found


def extract_knobs(root: Path) -> dict[str, Knob]:
    """Walk a source tree and return knobs keyed by their name (last one wins)."""
    collected: dict[str, Knob] = {}
    if not root.exists():
        return collected
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIR_NAMES for part in rel_parts[:-1]):
            continue
        suffix = path.suffix.lower()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        rel = str(path.relative_to(root))
        knobs: list[Knob] = []
        if suffix in PYTHON_SUFFIXES:
            knobs = extract_python(text, rel)
        elif suffix in JS_SUFFIXES:
            knobs = extract_js(text, rel)
        for knob in knobs:
            collected[knob.name] = knob
    return collected
