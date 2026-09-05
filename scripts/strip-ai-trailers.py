#!/usr/bin/env python3
"""commit-msg hook: keep only the subject line.

This repo commits with plain, one-line messages — no body, no description, and
no "Co-Authored-By: Claude ..." / "Claude-Session: ..." trailers. See CLAUDE.md.
Dropping everything after line 1 subsumes trailer stripping: a trailer never
lives on the subject line.

Note: this also drops the "This reverts commit <sha>." body that `git revert`
generates. Put the sha in the subject if you need it.
"""

import sys


def subject_only(lines: list[str]) -> list[str]:
    return lines[:1]


def main() -> int:
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(subject_only(lines))
    return 0


def _self_check() -> None:
    assert subject_only(
        [
            "feat: add thing\n",
            "\n",
            "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\n",
            "Claude-Session: https://x\n",
        ]
    ) == ["feat: add thing\n"]

    assert subject_only(
        [
            "fix: tighten the guard\n",
            "\n",
            "Long explanation that this repo does not want.\n",
            "Second paragraph.\n",
        ]
    ) == ["fix: tighten the guard\n"]

    assert subject_only(["chore: no trailing newline"]) == [
        "chore: no trailing newline"
    ]
    assert subject_only([]) == []

    print("ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        sys.exit(_self_check())
    else:
        sys.exit(main())
