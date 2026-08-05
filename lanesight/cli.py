"""Command-line interface for LaneSight.

Allows standalone routing/geocoding and JSON export without the Streamlit
UI, e.g.: ``python -m lanesight route "San Bernardino, CA" "Oakland, CA"``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from lanesight.core.router import Config, Router


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lanesight",
        description="LaneSight routing & geocoding engine (JSON output).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route", help="Compute a route between two locations.")
    route.add_argument("origin", help="Origin location string.")
    route.add_argument("destination", help="Destination location string.")
    route.add_argument(
        "--output",
        "-o",
        help="Write JSON to a file instead of stdout.",
    )
    route.add_argument(
        "--osrm-base-url",
        default=None,
        help="Override the OSRM server base URL.",
    )
    route.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable INFO-level logging to stderr.",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "route":
        return _run_route(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_route(args: argparse.Namespace) -> int:
    if args.verbose:
        logging.basicConfig(
            level=logging.INFO, format="[LaneSight] %(levelname)s: %(message)s"
        )

    if args.osrm_base_url:
        config = Config(osrm_base_url=args.osrm_base_url)
    else:
        config = Config()

    router = Router(config)
    try:
        result = router.route(args.origin, args.destination)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    payload = result.to_json() + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload)
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())