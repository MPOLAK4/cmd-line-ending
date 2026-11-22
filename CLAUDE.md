# CSC299 portfolio: shared instructions

These rules apply to every project in this portfolio: `web-app-demo`,
`webapp-game`, and `cmd-line-ending`. Each project is its own git repo;
this repo only holds the README that links to them.

## Always write unit tests

- Whenever you create or change application code, write unit tests for it in the
  same step. Do not hand over an app without tests.
- Keep all tests in a top-level `tests/` folder, separate from the app code, so
  they are easy to leave out of a release.
- Use the standard test tool for the language. In this project that is Python's
  built-in `unittest` (no installs): `python -m unittest discover -s tests -v`.
  Run the tests before saying a change is done, and show me the result.
- Explain what each test checks and why, so I can learn to write them myself.

## Tests are for development, not for releases

- Tests stay in git (never put `tests/` in `.gitignore`), but they must not be
  shipped in a release version of the program.
- Keep them out of release builds/packages, for example with
  `tests/ export-ignore` in `.gitattributes` (affects `git archive`) or by
  excluding `tests/` in the packaging config.
- Release code must not import from `tests/` or depend on test-only packages.

## General

- Follow the root `CLAUDE.md` for how to teach, explain, and commit.
- Keep each project small and readable; I should be able to understand all of it.

## What never goes in a repository

From the project spec sheet: "No transcripts (.jsonl files), no API keys or
passwords, no .venv or node_modules folders, and no personal information you
would not put on a public web page. These repositories are public."

- Never create, copy, or commit any of those things, in any project repo.
- Give every project a `.gitignore` that covers `*.jsonl`, `.env` and other secret
  files, `.venv/`, and `node_modules/`.
- Read keys and passwords from environment variables, never from source files.
- Before each commit, check what is staged (`git status`, `git diff --staged`) and
  stop if anything on this list is in it.

## Commits

- Whenever you fix, add, or modify a feature, make a commit right after, with a
  short message saying what changed. Do not batch unrelated changes together.
- Never push. I decide what gets pushed and when. Do not run `git push`, add
  remotes, or create GitHub repos unless I ask.

## Conventions for every round (cmd-line-ending)

- `spec.md` is the precise version of `problem.md`. When a requirement is added or
  changed, update `spec.md` first and commit it, then write tests, then the code.
- Every test name starts with the sub-requirement ID it checks, for example
  `test_R2_6_missing_file_is_skipped_...`. Each statement in `spec.md` should have at
  least one test; do not weaken a test to make it pass unless the test is wrong, and
  say so when that happens.
- Tests must never touch real user files or the real cache. Subclass `AppTestCase`
  in `tests/helpers.py` (it points `CMD_LINE_ENDING_HOME` at a temporary folder), and
  create test files with `write_bytes`, never text mode, because Windows and Git
  can silently rewrite line endings in text mode.
- Decisions that had real alternatives get a Y-statement record in
  `docs/decisions/`, numbered in order (`0004-...md` is next). Do not edit an
  accepted record; add a new one that supersedes it.
- Standard library only, Python 3.12+. No new dependencies.
- Never undo or amend a commit (no `reset`, `revert`, `commit --amend`, rebase).
  Fix mistakes with a new commit.
- Write a handoff file only when I ask for one.
