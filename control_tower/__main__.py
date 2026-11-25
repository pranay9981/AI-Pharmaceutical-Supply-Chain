"""Command-line entry point for the synthetic control tower."""

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .database import DEFAULT_DATABASE, DISCLAIMER, connect_database, initialize_database, market_supply_trace


def main() -> int:
    parser = argparse.ArgumentParser(description=DISCLAIMER)
    commands = parser.add_subparsers(dest="command")
    initialize = commands.add_parser("init-db", help="Create a new SQLite database")
    initialize.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    initialize.add_argument("--sample", action="store_true", help="Load the Week 2 sample records")
    trace = commands.add_parser("trace", help="Trace a market shipment to its procurement records")
    trace.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    trace.add_argument("--shipment", required=True)
    args = parser.parse_args()

    try:
        if args.command == "init-db":
            initialize_database(args.database, sample=args.sample)
            print(f"Created {args.database}")
            return 0
        if args.command == "trace":
            with closing(connect_database(args.database, read_only=True)) as connection:
                rows = market_supply_trace(connection, args.shipment)
            if not rows:
                parser.exit(1, f"No linked market supply records found for {args.shipment}.\n")
            print(json.dumps({"disclaimer": DISCLAIMER, "records": [dict(row) for row in rows]}, indent=2))
            return 0
    except (OSError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")

    print("Pharmaceutical Supply Chain Control Tower")
    print(DISCLAIMER)
    print("Week 2 SQLite data model")
    print("Use init-db --sample to create the linked demo database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
