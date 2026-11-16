"""Command-line interface for upgrade-guard-helper."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from upgrade_guard_helper import __version__
from upgrade_guard_helper.compare import compare_trees
from upgrade_guard_helper.fetch import HTTPError, URLError, fetch_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="upgrade-guard-helper",
        description=(
            "Diff default parameters and config constants (knobs) between two "
            "versions of a dependency. Prints a report; never overwrites input."
        ),
    )
    parser.add_argument("--old", type=Path, help="Path to the older source tree")
    parser.add_argument("--new", type=Path, help="Path to the newer source tree")
    parser.add_argument("--package", help="PyPI or npm package name to download")
    parser.add_argument("--old-version", dest="old_version", help="Older package version")
    parser.add_argument("--new-version", dest="new_version", help="Newer package version")
    parser.add_argument(
        "--ecosystem",
        choices=("pypi", "npm"),
        default="pypi",
        help="Registry to use with --package (default: pypi)",
    )
    parser.add_argument(
        "--write",
        metavar="FILE",
        help="Write the report to FILE (for example report.tidy.txt). Never overwrites the sources.",
    )
    parser.add_argument("--version", action="version", version=f"upgrade-guard-helper {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    tmp: tempfile.TemporaryDirectory[str] | None = None
    try:
        if args.old and args.new:
            old_root = args.old
            new_root = args.new
            old_label = str(args.old)
            new_label = str(args.new)
        elif args.package and args.old_version and args.new_version:
            tmp = tempfile.TemporaryDirectory(prefix="upgrade-guard-")
            base = Path(tmp.name)
            try:
                old_root = fetch_package(
                    args.package, args.old_version, base / "old", args.ecosystem
                )
                new_root = fetch_package(
                    args.package, args.new_version, base / "new", args.ecosystem
                )
            except (HTTPError, URLError, FileNotFoundError, OSError, ValueError) as err:
                print(f"upgrade-guard-helper: download failed: {err}", file=sys.stderr)
                return 1
            old_label = f"{args.package}=={args.old_version}"
            new_label = f"{args.package}=={args.new_version}"
        else:
            parser.error("give --old and --new, or --package with --old-version and --new-version")
            return 2

        if not old_root.exists() or not new_root.exists():
            print("upgrade-guard-helper: source path does not exist", file=sys.stderr)
            return 1
        result = compare_trees(old_root, new_root, old_label, new_label)
    finally:
        if tmp is not None:
            tmp.cleanup()

    report = result.report()
    if args.write:
        dest = Path(args.write)
        dest.write_text(report, encoding="utf-8")
        sys.stderr.write(f"Wrote {dest}\n")
    else:
        sys.stdout.write(report)
        if report and not report.endswith("\n"):
            sys.stdout.write("\n")
    return 0 if not result.changes else 1


if __name__ == "__main__":
    sys.exit(main())
