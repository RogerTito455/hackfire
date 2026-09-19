# Local setup: `pnpm setup` is a pnpm built-in, and the backend was not reading `.env`

**Date:** 2026-09-19 · **Area:** Setup

## What happened

1. `pnpm setup` failed with `ERR_PNPM_BAD_SHELL_SECTION` instead of installing dependencies. On a machine without a pnpm section in `~/.bashrc`, it would have edited the shell profile and still installed nothing.
2. Keys in the repo-root `.env` never reached the backend: `config.py` reads `os.environ`, but nothing loaded the file.
3. A `.env` with pasted notes (a curl snippet, `/** … */` blocks) parses only partially. The parser warns `could not parse statement starting at line N` and keeps going, so a variable with a slightly different name from `.env.example` just reads as empty.

## Why

1. `setup` is a built-in pnpm command (it configures `PNPM_HOME`), and built-ins win over scripts with the same name.
2. The skeleton was written before anyone had keys, so the gap never showed.

## What we do about it

1. The script is now `pnpm bootstrap`. `pnpm setup` should never be run in this repo.
2. `config.py` calls `load_dotenv(REPO_ROOT / ".env")` (python-dotenv, added with `uv add`). Variables already set in the environment still win, so tests and the hosting platform are unaffected.
3. `.env` holds only `KEY=value` lines and `#` comments, with the exact names from `.env.example`. Notes go in the docs, without the values.
