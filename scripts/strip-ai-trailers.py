#!/usr/bin/env python3
"""commit-msg hook: strip AI-assistant attribution trailers.

This repo commits with plain, simple messages — no "Co-Authored-By: Claude ..."
or "Claude-Session: ..." trailers. See CLAUDE.md.
"""

import re
import sys

CO_AUTHOR_CLAUDE_RE = re.compile(r"^Co-Authored-By:.*claude", re.IGNORECASE)
CLAUDE_SESSION_RE = re.compile(r"^Claude-Session:", re.IGNORECASE)


def strip_trailers(lines: list[str]) -> list[str]:
    kept = [
        line
        for line in lines
        if not CO_AUTHOR_CLAUDE_RE.match(line) and not CLAUDE_SESSION_RE.match(line)
    ]
    while kept and kept[-1].strip() == "":
        kept.pop()
    return kept


def main() -> int:
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(strip_trailers(lines))
    return 0


def _self_check() -> None:
    given = [
        "feat: add thing\n",
        "\n",
        "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\n",
        "Claude-Session: https://x\n",
    ]
    assert strip_trailers(given) == ["feat: add thing\n"]

    given_human_coauthor = [
        "feat: pair on thing\n",
        "\n",
        "Co-Authored-By: Jane Doe <jane@example.com>\n",
    ]
    assert (
        strip_trailers(given_human_coauthor) == given_human_coauthor
    )  # human co-authors are untouched

    print("ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _self_check()
    else:
        sys.exit(main())
