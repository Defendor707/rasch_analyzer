# Rasch Analyzer Documentation

## Quick Start

1. Create and populate `.env` (see `.env.example`).
2. Create a virtualenv and install deps:
   - `python -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Initialize the database: `python setup_database.py`.
4. Run bots: `python run_bots.py`.

## Project Structure

- `bot/`, `student_bot/`: core logic
- `data/`: input/output data (uploads, results)
- `docs/`: documentation
- `run_bots.py`: entrypoint
- `setup_database.py`: DB setup

## Deployment (outline)

- Containerized via `Dockerfile`.
- Provide environment variables via `.env`.
- Reverse proxy (e.g., Nginx) recommended.

## Testing & CI

- Run tests: `pytest`
- Lint: `ruff check .`
- Format: `black .`
- CI: GitHub Actions runs lint and tests on PRs.
