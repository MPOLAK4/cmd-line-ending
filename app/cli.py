"""Command-line interface: parses arguments and prints results."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from app import history
from app.lineendings import STYLES, convert, revert, scan


def format_line(status: str, detail: str, path) -> str:
    """One output line: a 12-wide status column, a 14-wide detail column, the path."""
    return f"{status:<12}{detail:<14}{path}"


def cmd_scan(args) -> int:
    try:
        reports = scan(Path(args.path))
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    changeable = 0
    for report in reports:
        if report.changeable:
            changeable += 1
            detail = f"{report.status} -> {report.suggestion}"
            print(format_line("changeable", detail, report.path))
        else:
            print(format_line("skipped", report.status, report.path))
    print(f"{changeable} changeable, {len(reports) - changeable} skipped")
    return 0


def cmd_convert(args) -> int:
    try:
        results = convert(Path(args.path), args.to)
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    counts = {"converted": 0, "unchanged": 0, "skipped": 0}
    for result in results:
        counts[result.outcome] += 1
        print(format_line(result.outcome, result.detail, result.path))
    print(f"{counts['converted']} converted, {counts['unchanged']} unchanged, "
          f"{counts['skipped']} skipped")

    # R2.1: remember what really changed, so the user can look it up or revert it.
    changed = [(r.path, r.original) for r in results if r.outcome == "converted"]
    try:
        history.record(args.to, changed)
    except OSError:
        print("warning: could not save history", file=sys.stderr)  # R2.7
    return 0


def cmd_history(args) -> int:
    entries = history.load()["entries"]
    if not entries:
        print("No recent changes.")
        return 0
    for entry in reversed(entries):  # newest first (R2.4)
        when = datetime.strptime(entry["time"], history.TIME_FORMAT).strftime("%Y-%m-%d %H:%M:%S")
        count = len(entry["files"])
        noun = "file" if count == 1 else "files"
        print(f"#{entry['id']}  {when} UTC  to {entry['to']}  {count} {noun}")
        for recorded in entry["files"]:
            print(f"    {recorded['path']}")
    return 0


def cmd_revert(args) -> int:
    entries = history.load()["entries"]
    if not entries:
        print("error: no recent changes to revert", file=sys.stderr)
        return 1
    if args.id is None:
        entry = entries[-1]  # the newest
    else:
        entry = next((e for e in entries if e["id"] == args.id), None)
        if entry is None:
            print(f"error: no history entry #{args.id}", file=sys.stderr)
            return 1

    results = revert(entry)
    reverted = 0
    for result in results:
        reverted += result.outcome == "reverted"
        print(format_line(result.outcome, result.detail, result.path))
    print(f"{reverted} reverted, {len(results) - reverted} skipped")

    try:
        history.remove(entry["id"])  # R2.6: the entry is used up either way
    except OSError:
        print("warning: could not save history", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app",
        description="Find text files whose line endings can be changed, and change them.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    scan_parser = commands.add_parser(
        "scan", help="report line endings in a file or directory (changes nothing)"
    )
    scan_parser.add_argument("path", help="a file or a directory")
    scan_parser.set_defaults(func=cmd_scan)

    convert_parser = commands.add_parser(
        "convert", help="change the line endings of every changeable file in a path"
    )
    convert_parser.add_argument("path", help="a file or a directory")
    convert_parser.add_argument(
        "--to", required=True, choices=STYLES, help="the line ending style to change to"
    )
    convert_parser.set_defaults(func=cmd_convert)

    history_parser = commands.add_parser("history", help="list recent changes, newest first")
    history_parser.set_defaults(func=cmd_history)

    revert_parser = commands.add_parser(
        "revert", help="undo a recent change (the newest one unless you give its id)"
    )
    revert_parser.add_argument("id", nargs="?", type=int, help="the #number shown by history")
    revert_parser.set_defaults(func=cmd_revert)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
