from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BINDINGS = REPO / "frontend" / "bindings"


def strip_ts_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end == -1:
                break
            i = end + 2
            if i < n and text[i] == "\n":
                i += 1
            continue
        if text.startswith("//", i):
            end = text.find("\n", i)
            if end == -1:
                break
            i = end + 1
            continue
        out.append(text[i])
        i += 1
    cleaned = "".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def main() -> None:
    if not BINDINGS.is_dir():
        return
    for path in sorted(BINDINGS.rglob("*")):
        if path.suffix not in {".ts", ".d.ts"}:
            continue
        original = path.read_text(encoding="utf-8")
        cleaned = strip_ts_comments(original)
        if cleaned:
            cleaned += "\n"
        if cleaned != original:
            path.write_text(cleaned, encoding="utf-8")


if __name__ == "__main__":
    main()
