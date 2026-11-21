# Spec: cmd-line-ending

This file turns the requirements in `problem.md` into small, testable statements.
`problem.md` is the source (R1, R2). Here each one is split into sub-requirements
(R1.1, R1.2, ...) so that every test can name exactly one of them.

## Round 1

Scope: scan, convert, history, revert. Stdlib only, Python 3.12+.

### Words used

- **Line ending style**: how a file marks the end of a line.
  - `lf` = the single byte `\n` (Linux, macOS, most tools)
  - `crlf` = the two bytes `\r\n` (Windows)
  - `cr` = the single byte `\r` (very old Mac files)
- **Text file**: a file with no NUL byte (`\0`) whose bytes are valid UTF-8.
- **Uniform**: every line ending in the file is the same style.
- **Changeable**: a text file that is uniform and has at least one line ending.

### Commands

    python -m app scan PATH                  (R1)
    python -m app convert PATH --to lf|crlf|cr   (R1, R2)
    python -m app history                    (R2)
    python -m app revert [ID]                (R2)

`PATH` is a file or a directory.

### R1: find changeable files and say what to change them to

- **R1.1** `scan PATH` accepts a file or a directory. If `PATH` does not exist it
  prints an error to stderr and exits with code 1.
- **R1.2** The style of a file is `lf`, `crlf` or `cr`, found by counting `\r\n`
  pairs first, then lone `\n`, then lone `\r`.
- **R1.3** A file is *changeable* only if it is a text file, is uniform, and has at
  least one line ending. Every other file is *skipped*, with exactly one reason:
  `binary` (a NUL byte or not valid UTF-8), `mixed` (more than one style), or
  `no line endings` (empty, or a single line with no ending).
- **R1.4** For each changeable file, `scan` shows its current style and a suggested
  target: `crlf` -> `lf`, `lf` -> `crlf`, `cr` -> `lf`.
- **R1.5** Scanning a directory is recursive and visits files in sorted order. It
  does not enter directories named `.git`, `.hg`, `.svn`, `node_modules`,
  `__pycache__` or `.venv`.
- **R1.6** `scan` never modifies any file.
- **R1.7** Output is one line per file, then one summary line:

      changeable  crlf -> lf  path/to/a.txt
      skipped     binary      path/to/pic.png
      2 changeable, 1 skipped

  The summary uses the counts of changeable and skipped files.
- **R1.8** `convert PATH --to STYLE` changes every changeable file under `PATH` to
  `STYLE`. Files already in `STYLE` are left untouched. Skipped files are left
  untouched and listed with their reason. All bytes other than line endings stay
  exactly the same. Output is one line per file, then a summary line:

      converted   crlf -> lf    path/to/a.txt
      unchanged   already lf    path/to/b.txt
      skipped     binary        path/to/pic.png
      1 converted, 1 unchanged, 1 skipped

  `convert` exits 0 even when some files were skipped, and exits 1 (error on
  stderr) if `PATH` does not exist.
- **R1.9** A file is written safely: the new content goes to a temporary file in the
  same directory, which then replaces the original. No temporary file is left
  behind, and the original's permissions are kept.

### R2: small cache of recent changes, with revert

- **R2.1** Each `convert` that changes at least one file adds exactly one history
  entry with: an id, a UTC timestamp, the target style, and for each changed file
  its absolute path and its original style. Converting one file gives an entry with
  one file (a single change); converting a directory gives one entry with all its
  files (a batch). A `convert` that changes nothing adds no entry.
- **R2.2** The cache is one JSON file, `history.json`, kept in a folder outside the
  scanned files: `~/.cmd-line-ending/` by default, or the folder named by the
  environment variable `CMD_LINE_ENDING_HOME` when it is set.
- **R2.3** The cache keeps only the 50 newest entries; older ones are dropped.
- **R2.4** `history` lists entries newest first. Each entry shows its id, time,
  target style and file count, followed by its file paths, one per line and
  indented by four spaces:

      #2  2026-11-21 17:30:02 UTC  to lf  2 files
          /abs/path/a.txt
          /abs/path/b.txt

  With no entries it prints `No recent changes.`
- **R2.5** `revert [ID]` puts every file of that entry back to its original style.
  Without `ID` it uses the newest entry. An unknown id, or an empty history, prints
  an error to stderr and exits with code 1.
- **R2.6** `revert` skips a file that no longer exists or whose current style is no
  longer the one the entry recorded as the target (someone edited it since), and
  says so. After the revert the entry is removed from the cache. Output is one
  line per file, then a summary line:

      reverted    lf -> crlf    /abs/path/a.txt
      skipped     changed since /abs/path/b.txt
      skipped     missing       /abs/path/c.txt
      1 reverted, 2 skipped
- **R2.7** A missing, unreadable or corrupt `history.json` is treated as an empty
  history; it never crashes a command.

### Out of scope for Round 1

Dry-run mode, ignore files, encodings other than UTF-8, byte-order-mark handling,
following symbolic links, and a way to convert only some files in a directory.
