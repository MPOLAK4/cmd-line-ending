"""Command-line interface: parses arguments and prints results."""

import argparse
import sys
from pathlib import Path

from app.lineendings import STYLES, convert, scan


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
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
