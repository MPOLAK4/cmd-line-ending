# Handoff: end of round 1

For a fresh session starting round 2. Read this, then `problem.md`, `spec.md`,
`CLAUDE.md` and `docs/decisions/`. Standing rules (tests, commits, never push, never
amend) are in `CLAUDE.md`, not here.

## Current state

Round 1 is complete: **R1** (scan and convert) and **R2** (history and revert) from
`problem.md` are implemented and tested.

- 78 tests, all pass, 1 skipped (the symlink test: this Windows account cannot create
  symlinks, so it skips itself).
- Last round-1 commit when this was written: `9254f2f` ("README: real run instructions
  ..."). 20 commits total. Nothing has been pushed.
- Working tree was clean before this handoff. `handoff-round-1.md` and the new section
  at the bottom of `CLAUDE.md` are **uncommitted**, waiting for the owner to read and
  edit them.

### Files

| Path | Purpose |
| --- | --- |
| `app/lineendings.py` | `detect_style`, `list_files`, `scan`, `convert_bytes`, `convert`, `revert` |
| `app/history.py` | The cache: `cache_path`, `load` (validates), `save`, `record`, `remove` |
| `app/fileio.py` | `write_atomic`: temp file in the same folder, then `os.replace` |
| `app/cli.py` | argparse, the four commands, output formatting |
| `spec.md` | Requirement IDs R1.1 to R1.9 and R2.1 to R2.7, with exact output formats |
| `tests/helpers.py` | `AppTestCase`: temp work folder, private cache folder, `run_app()` |
| `tests/test_{scan,convert,history,revert}.py` | One class group per area, test names start with the ID |
| `docs/decisions/0001..0003` | Y-statement records (see "Decisions" below) |

`NEXT-SESSION.md` also exists but is excluded from git (`.git/info/exclude`) and is
now out of date. It was the round-1 start prompt. Ignore or delete it.

## How to run

From the repo folder, Python 3.12+, no installs:

    python -m app --help
    python -m app scan PATH
    python -m app convert PATH --to lf|crlf|cr
    python -m app history
    python -m app revert [ID]

`PATH` is a file or folder. Exit codes: 0 ok, 1 error (bad path, nothing/unknown id to
revert), 2 bad arguments (argparse). The cache is `~/.cmd-line-ending/history.json`;
**set `CMD_LINE_ENDING_HOME` to a scratch folder when trying things by hand**, or you
will write to the real one.

## How to run the tests

    python -m unittest discover -s tests -v

Run it from the repo root (`python -m` puts the current folder on the import path, which
is how `import app` works). The suite takes about 2 seconds. Tests use mocks in three
places: `Path.read_bytes` (unreadable file), `os.replace` (failed write) and
`Path.home` (default cache location), so a failure in those tests can mean the code
moved the call, not that behavior broke.

## Decisions made in round 1, and why

The owner chose these (answers to my questions):
- **Changeable** = text file with exactly one style. Binary and mixed files are listed
  as skipped, never converted.
- **Target**: the user picks with `--to`; `scan` only *suggests* (crlf -> lf, lf -> crlf,
  cr -> lf).
- **R2 scope**: `history` and `revert` are in, cache keeps 50 entries.
- **unittest, not pytest** (record 0003). `CLAUDE.md` was changed to match the README.

I decided these without being asked:
- **Revert uses the recorded style, not backups** (record 0001). Converting between
  styles is lossless for uniform files, so the old style is enough to rebuild the
  bytes. Cost: a file edited after the convert is skipped on revert.
- **Safe writes** (record 0002): temp file next to the target, then `os.replace`. The
  cache is written the same way.
- **Text** means no NUL byte and valid UTF-8. UTF-16 and Latin-1 files count as
  `binary`. Empty and one-line files are skipped as `no line endings`.
- **Walk rules**: recursive, sorted by path, skips `.git .hg .svn node_modules
  __pycache__ .venv`, ignores symlinks. Extra skip reasons: `unreadable`,
  `write failed`.
- **One history entry per `convert` run that changed something** (a single file is a
  one-file entry, a folder is a batch). Runs that change nothing record nothing.
- **Ids come from a stored `next_id` counter and are never reused**, so an old id from
  earlier output can never point at a different change.
- **Revert** only touches a file whose current style equals the recorded target. The
  entry is **removed afterward even if some files were skipped**, and revert does not
  create its own entry.
- **Damaged or missing cache = empty history.** If the cache cannot be saved, the
  command still does its work and prints `warning: could not save history`.
- Sub-requirement IDs (R1.1 ...) exist only in `spec.md`. `problem.md` still has just
  R1 and R2 as the owner wrote them.

## Unresolved

- **`problem.md` R1 wording is still the vague original.** `NEXT-SESSION.md` said the
  owner would update it after approving a testable wording. That has not happened;
  `spec.md` carries the precise version. Ask before touching `problem.md` (the owner
  writes it).
- **Revert drops the whole entry even when files were skipped**, so skipped files
  cannot be retried. Possible round-2 change: keep the unreverted files in the entry.
- **`origin` still points at `cmd-rar`**, not this project. The owner said they will fix
  it. Do not touch remotes or push.
- Not done, listed as out of scope in `spec.md`: dry-run, no confirmation prompt before
  `convert`, other encodings, BOM handling, following symlinks, converting only some
  files in a folder, locking if two runs use the cache at once.
- Minor inconsistency: a *symlinked file* given directly as `PATH` is ignored, but a
  *symlinked folder* given as `PATH` is walked (only symlinks found *inside* a walk
  are ignored). Not covered by a test.
- Between reading a file and replacing it there is a tiny window where another program
  could edit it; that edit would be lost. Accepted, not handled.
- Round 1 skipped the "session start" steps in the parent `CLAUDE.md` (re-fetching the
  instructor's instructions, `course-instructions/` bookkeeping, coaching notes,
  `topics/questions.md`) because the round prompt said to use only this repository.
  Follow the parent `CLAUDE.md` again unless the round-2 prompt says otherwise.

## Warnings

- **Git `core.autocrlf=true` is set system-wide on this machine**, and this app edits
  line endings. Commits print "LF will be replaced by CRLF" warnings; they are harmless
  here (files in the working copy are LF, blobs are LF). But if you run `convert` on
  this repo's own files, git will show noisy diffs. Never point `convert` at this repo
  without a reason, and never commit the result.
- **Always create test fixtures with `write_bytes`** (see `AppTestCase.write`). Text
  mode on Windows would silently change the very bytes under test.
- **Tests must use `AppTestCase`.** Without it, a test that calls `convert` writes to
  the real `~/.cmd-line-ending/history.json`. I checked that the round-1 suite did
  not create that folder.
- `tests/helpers.py` is imported as plain `helpers`, which works because
  `unittest discover -s tests` puts `tests/` on the path. Running a test file some
  other way (for example `python -m unittest tests.test_scan`) may fail to import it.
- The first commits of each slice are **intentionally failing tests** (`6866652`,
  `2b8e7af`, `c244561`), committed before the code. Do not "fix" history; use
  `git log` to see the order.
- One test assertion was wrong and was corrected in `576b70c` (the id was not expected
  in the error after the only entry had been reverted). If a test fails in round 2,
  check whether the spec or the test is wrong before changing code.
- `app/__pycache__/` and `tests/__pycache__/` exist locally and are git-ignored.
- Release rule: `tests/` is `export-ignore` in `.gitattributes`; `git archive HEAD`
  contains no test files (checked). Keep `app/` from importing anything in `tests/`.
