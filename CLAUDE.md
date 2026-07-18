# CLAUDE.md

This repository uses `AGENTS.md` as the canonical instruction file. Claude should treat this file as a short bridge and defer to `AGENTS.md` for project rules.

Before editing, read and follow:

- `AGENTS.md`
- `superpowers/specs/2026-06-04-aes-system-design.md`
- `superpowers/plans/2026-06-04-aes-api.md`

Core project intent: build an assistive LLM-based essay correction API that helps teachers handle the slow, repetitive, and inconsistent correction workload in Ensino Fundamental. The system must produce rubric-based feedback, traceability, privacy safeguards, and teacher review.

Prefer existing FastAPI, SQLAlchemy async, Alembic, Taskiq, and Pydantic v2 patterns already present in the backend. Mock LLMs and external services in tests.

Do not treat the system as an autonomous final grader. It is a teacher-support tool.

## Commit messages

Use plain, simple commit messages — no `Co-Authored-By: Claude ...` or `Claude-Session: ...` trailers. This overrides Claude Code's default commit template for this repository. A `commit-msg` git hook (`scripts/strip-ai-trailers.py`, wired via `.pre-commit-config.yaml`) strips those trailers automatically if they slip through, but don't rely on it — just write the plain message.
