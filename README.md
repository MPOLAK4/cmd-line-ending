# cmd-line-ending

A command-line app (no window, no web page). The problem it solves is in
[problem.md](problem.md).

## How to run

Needs Python 3.12 or newer. No libraries to install. Run these from this folder.

    python -m app --help
    python -m app scan PATH                      # report only, changes nothing
    python -m app convert PATH --to lf|crlf|cr   # change the line endings
    python -m app history                        # recent changes, newest first
    python -m app revert [ID]                    # undo the newest change, or #ID

`PATH` is a file or a folder. `scan` lists each file as `changeable` (with the
style it has now and the one it suggests) or `skipped` (binary, mixed endings, or no
line endings at all). `convert` only touches changeable files and remembers what it
changed in `~/.cmd-line-ending/history.json` (set `CMD_LINE_ENDING_HOME` to use
another folder). The exact rules are in [spec.md](spec.md).

## How to run the tests

    python -m unittest discover -s tests -v

## Project index

| Card | What it is |
| --- | --- |
| `problem.md` | The problem and the numbered requirements (R1, R2, ...). Written by me. |
| `README.md` | This file: how to run, how to test, and this index. |
| `CLAUDE.md` | Instructions the coding assistant follows in this project. |
| `.gitignore` | Files git must never track (transcripts, secrets, virtual environments). |
| `.gitattributes` | Keeps `tests/` out of release archives (`git archive`). |
| `spec.md` | `problem.md` made precise: numbered sub-requirements (R1.1, R2.3, ...). |
| `docs/decisions/` | Decision records: why the project does things the way it does. |
| `app/` | The program's source code. |
| `tests/` | Unit tests; they name the requirement IDs they check. Not part of a release. |
