# cmd-line-ending

A command-line app (no window, no web page). The problem it solves is in
[problem.md](problem.md).

## How to run

Needs Python 3.12 or newer. No libraries to install.

    python -m app --help

(The `app` package does not exist yet; this command works once the first code is added.)

## How to run the tests

    python -m unittest discover -s tests -v

## Project index

| Card | What it is |
| --- | --- |
| `problem.md` | The problem and the numbered requirements (R1, R2, ...). Written by me. |
| `README.md` | This file: how to run, how to test, and this index. |
| `CLAUDE.md` | Instructions the coding assistant follows in this project. |
| `.gitignore` | Files git must never track (transcripts, secrets, virtual environments). |
| `app/` *(coming)* | The program's source code. |
| `tests/` *(coming)* | Unit tests; they name the requirement IDs they check. Not part of a release. |
