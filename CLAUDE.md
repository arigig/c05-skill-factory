# C05 — Application Migration Skill Factory

Single source of truth for scope and acceptance criteria: [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md). Do not invent requirements beyond that file; if something is unclear or missing, stop and ask.

## Commands

| Task | Command |
|---|---|
| Create/activate venv | `py -3.14 -m venv .venv` then `.venv\Scripts\activate` |
| Install dependencies | `pip install -r requirements.txt` |
| Run app locally | `uvicorn app.main:app --reload --port 8000` |
| Run tests | `pytest` |
| Run everything via Docker | `docker compose up --build` |
| Check installed tool versions | `py -3.14 scripts/check_env.py` |

## Allow / Ask / Deny rules

- **Deny:** reading, editing, or writing `.env` (holds the live Anthropic API key — never read its contents, never commit it).
- **Deny:** `git push --force`, `git reset --hard`, deleting branches, and any destructive git operation.
- **Deny:** committing or pushing any file matching secret patterns (`*.key`, `*.pem`, `.env*` except `.env.example`).
- **Ask:** before `git push`, before creating/merging pull requests, before `docker compose down -v` or any volume-deleting command, before installing new global tools.
- **Allow:** local file edits within this repo, running tests, running the app locally, `git add`/`git commit` on non-secret files.
- **Agents never write to the catalog or push to Git** — only a human reviewer approval can do that (see Non-negotiable rules in REQUIREMENTS.md §5).

These rules are also enforced mechanically where possible in `.claude/settings.json` (permission deny list for `.env`).

## Definition of done (per iteration)

Each iteration in REQUIREMENTS.md §4 has a stated pass/fail check. An iteration is **not done** until:
1. Its stated check passes (e.g. "Iteration 1: `docker compose up` serves the page and the health check returns 200; CI is green").
2. No critical security, privacy, or safety gap is introduced (REQUIREMENTS.md §1).
3. Any metric reported is from a real run — unmeasured benefits are labelled *projected* (REQUIREMENTS.md §5).
4. A human has reviewed and approved before anything is accepted into a reusable catalog (REQUIREMENTS.md §5).

Do not move to the next iteration until the current one's check passes.
