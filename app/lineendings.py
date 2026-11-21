"""Detecting and scanning line endings (R1). Nothing here changes a file."""

import os
from dataclasses import dataclass
from pathlib import Path

from app.fileio import write_atomic

# R1.5: folders we never look inside.
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv"}

# R1.4: what we suggest changing each style to.
SUGGESTION = {"crlf": "lf", "lf": "crlf", "cr": "lf"}

STYLES = ("lf", "crlf", "cr")


def detect_style(data: bytes) -> str:
    """Classify the raw bytes of a file (R1.2, R1.3).

    Returns "lf", "crlf" or "cr" for a changeable file, otherwise the reason it
    is not changeable: "binary", "mixed" or "no line endings".
    """
    if b"\x00" in data:
        return "binary"
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return "binary"

    # Count "\r\n" first. Then a "\n" that is NOT part of a "\r\n" is a lone LF,
    # and a "\r" that is NOT part of a "\r\n" is a lone CR.
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf

    present = [style for style, n in (("lf", lf), ("crlf", crlf), ("cr", cr)) if n]
    if not present:
        return "no line endings"
    if len(present) > 1:
        return "mixed"
    return present[0]


@dataclass(frozen=True)
class FileReport:
    """What we found out about one file."""

    path: Path
    status: str  # a style ("lf", "crlf", "cr") or a skip reason

    @property
    def changeable(self) -> bool:
        return self.status in STYLES

    @property
    def suggestion(self) -> str | None:
        return SUGGESTION.get(self.status)


def inspect_file(path: Path) -> FileReport:
    try:
        return FileReport(path, detect_style(path.read_bytes()))
    except OSError:
        return FileReport(path, "unreadable")


def list_files(root: Path) -> list[Path]:
    """The files to look at for a file-or-directory argument (R1.1, R1.5).

    Symbolic links are ignored. Raises FileNotFoundError if root does not exist.
    """
    if not root.exists():
        raise FileNotFoundError(f"no such file or directory: {root}")
    if root.is_file():
        return [] if root.is_symlink() else [root]

    found = []
    for folder, dirnames, filenames in os.walk(root):
        # Editing dirnames in place tells os.walk not to enter those folders.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(folder) / name
            if not path.is_symlink():
                found.append(path)
    return sorted(found)


def scan(root: Path) -> list[FileReport]:
    """Report on every file under root without modifying anything (R1.6)."""
    return [inspect_file(p) for p in list_files(root)]


# ---------------------------------------------------------------------------
# Converting (R1.8, R1.9)
# ---------------------------------------------------------------------------

LINE_BREAK = {"lf": b"\n", "crlf": b"\r\n", "cr": b"\r"}


def convert_bytes(data: bytes, to: str) -> bytes:
    """Return data with every line ending replaced by the `to` style.

    Order matters: turn "\\r\\n" into "\\n" first, so the following step (lone
    "\\r" into "\\n") cannot split a CRLF into two endings.
    """
    unified = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return unified.replace(b"\n", LINE_BREAK[to])


@dataclass(frozen=True)
class ConvertResult:
    """What convert (or revert) did with one file."""

    path: Path
    outcome: str  # "converted", "unchanged", "reverted" or "skipped"
    detail: str  # e.g. "crlf -> lf", "already lf", "binary", "write failed"
    original: str | None = None  # the old style, set when outcome == "converted"


def convert(root: Path, to: str) -> list[ConvertResult]:
    """Convert every changeable file under root to the `to` style."""
    results = []
    for path in list_files(root):
        try:
            data = path.read_bytes()
        except OSError:
            results.append(ConvertResult(path, "skipped", "unreadable"))
            continue

        style = detect_style(data)
        if style not in STYLES:
            results.append(ConvertResult(path, "skipped", style))
        elif style == to:
            results.append(ConvertResult(path, "unchanged", f"already {to}"))
        else:
            try:
                write_atomic(path, convert_bytes(data, to))
            except OSError:
                results.append(ConvertResult(path, "skipped", "write failed"))
            else:
                results.append(ConvertResult(path, "converted", f"{style} -> {to}", style))
    return results


def revert(entry: dict) -> list[ConvertResult]:
    """Put the files of one history entry back to their original style (R2.5, R2.6).

    A file is only touched if it still has the style the entry says we changed it
    to. Otherwise someone has edited or removed it since, and we leave it alone.
    """
    to = entry["to"]
    results = []
    for recorded in entry["files"]:
        path, original = Path(recorded["path"]), recorded["from"]
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            results.append(ConvertResult(path, "skipped", "missing"))
            continue
        except OSError:
            results.append(ConvertResult(path, "skipped", "unreadable"))
            continue

        if detect_style(data) != to:
            results.append(ConvertResult(path, "skipped", "changed since"))
            continue
        try:
            write_atomic(path, convert_bytes(data, original))
        except OSError:
            results.append(ConvertResult(path, "skipped", "write failed"))
        else:
            results.append(ConvertResult(path, "reverted", f"{to} -> {original}"))
    return results
