# AGENTS.md

## Project Mission

This repository contains the software artifact needed to support a TCC about LLM-assisted essay correction in Ensino Fundamental.

Build an API that helps solve a specific educational problem: teachers need to correct many student essays with limited time, while students need frequent, clear, individualized feedback to improve their writing. The application must provide standardized, traceable, rubric-based LLM assistance without replacing the teacher's pedagogical judgment.

This is not an ENEM-only grader, a generic chatbot, or a replacement for teachers.

## Problem The Application Must Solve

In Ensino Fundamental, essay correction is often slow, inconsistent, and difficult to scale because it depends heavily on manual teacher review. This limits how often students receive detailed feedback and makes it harder to identify recurring writing difficulties across a class.

The application exists to:

- receive student essays in text or image form;
- organize correction work as asynchronous jobs;
- apply configurable writing rubrics appropriate for Ensino Fundamental;
- generate diagnostic feedback for each rubric criterion;
- make the correction traceable, auditable, and reproducible enough for academic analysis;
- give teachers a faster starting point for review, intervention, and classroom feedback.

The product must make the TCC viable by demonstrating that a real backend can operationalize this correction workflow. The repository should hold the application, tests, technical documentation, and implementation evidence. It should not depend on the TCC manuscript being present in the repo.

## Canonical Context

Read these before changing product behavior:

- `superpowers/specs/2026-06-04-aes-system-design.md` - system design and target architecture.
- `superpowers/plans/2026-06-04-aes-api.md` - current implementation plan aligned to this repository.
- `README.md` - inherited FastAPI boilerplate commands and conventions.

When these documents disagree, prefer this `AGENTS.md` for product intent, the system design for target architecture, the plan for current implementation sequencing, and the existing code for local conventions.

## Product Boundaries

- The system supports teacher review; it must not make autonomous high-stakes decisions.
- Focus on Ensino Fundamental, especially final years, with language and criteria appropriate for that audience.
- Use configurable rubrics aligned with BNCC/SAEB-style writing competencies.
- Initial rubric criteria are:
  - `adequacao_tema`
  - `estrutura_textual`
  - `coesao_coerencia`
  - `adequacao_ling`
  - `vocabulario`
- Feedback must be constructive, specific, age-appropriate, and grounded in evidence from the student's text.
- Do not claim real classroom validation, learning gains, or pedagogical efficacy unless the repo contains explicit evidence.
- Avoid punitive tone, unsupported diagnoses, bias against dialectal variation, and hallucinated references to text that is not present.

## Architecture Direction

Preserve the existing FastAPI backend structure and add AES functionality as vertical slices instead of rewriting the boilerplate.

Expected target shape:

- REST API for asynchronous correction jobs.
- Batch submission of essay text and/or image inputs.
- Object storage for original submissions and generated artifacts.
- Queue-backed workers for OCR and LLM correction.
- PostgreSQL persistence through SQLAlchemy async and Alembic migrations.
- LLM access through a provider abstraction, with structured outputs validated by Pydantic.
- Traceability for model name, prompt version, parameters, retries, raw provider metadata, and generated correction results.

Planned public endpoints include:

- `POST /api/v1/aes/jobs`
- `GET /api/v1/aes/jobs/{job_id}`
- `GET /api/v1/aes/jobs/{job_id}/results`
- `GET /api/v1/aes/models`
- `GET /health`

## Implementation Rules

- Follow existing repository patterns before introducing new abstractions.
- Keep changes scoped, reviewable, and reversible.
- Use Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, Taskiq, and the project's existing dependency management.
- Add persistent schema changes through Alembic migrations.
- Keep LLM prompts versioned as assets or structured templates; do not scatter large prompt strings across service code.
- Prefer deterministic LLM parameters for evaluation paths, such as low temperature and explicit model/prompt metadata.
- Validate structured LLM responses with Pydantic models before saving or returning them.
- Use retries and clear failure states for external services.
- Do not log secrets, raw student data, or personally identifiable information.
- Do not add new dependencies unless they materially reduce risk or complexity.
- Keep generated or user-facing Portuguese text clear, neutral, and suitable for school context.

## Testing And Verification

Before claiming completion, run the smallest checks that prove the changed behavior.

Typical backend checks:

```bash
cd backend
uv run pytest
uv run ruff check
uv run mypy src
```

Use narrower test commands when working on a small area.

Testing expectations:

- Unit tests mock LLM providers, OCR, queues, and object storage.
- API tests cover authentication, validation errors, job creation, job status, and results.
- Worker tests cover idempotency, retry/failure behavior, and persistence.
- Migration tests or at least migration import checks are required for schema changes.
- Do not require live network calls, real LLM keys, real student data, or production cloud services for normal tests.

## Security, Privacy, And Ethics

- Treat essay content as sensitive educational data.
- Use fake or synthetic essays in tests and examples.
- Keep API keys, cloud credentials, and provider secrets out of the repository.
- Redact or avoid raw student text in logs.
- Keep human-in-the-loop review explicit in data models, API responses, and documentation.
- If a feature could be interpreted as final grading, document that it is assistive and requires teacher review.

## Academic Integrity

- Align product claims with the educational problem described in this file.
- Distinguish implemented behavior from proposed future work.
- Do not invent citations, datasets, classroom results, or benchmark numbers.
- Evaluation claims should name their metric and dataset/source, for example agreement rate, QWK, rubric adherence, or functional test coverage.

## Editor And Agent Behavior

This repository intentionally keeps only two agent entry points:

- `AGENTS.md` for Codex and other agents that understand the AGENTS convention.

- `CLAUDE.md` for Claude, pointing back to this file.

- Start by reading the canonical context files relevant to the task.

- Prefer `rg` for repository search.

- Use existing commands and project tooling from `README.md` and `backend/pyproject.toml`.

- For code edits, keep style consistent with nearby files.

- Preserve user changes in the working tree.

- When asked for a plan, update the relevant plan file instead of only answering in chat.

- When asked to implement, edit, test, and report evidence.
