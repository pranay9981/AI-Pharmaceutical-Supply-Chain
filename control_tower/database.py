"""Initialise a new local database and read its evidence links."""

import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_DATABASE = Path("data/output/control_tower.sqlite3")
SCHEMA = Path(__file__).with_name("schema.sql")
SAMPLE = SCHEMA.parent.parent / "examples" / "week_02_sample.sql"
DISCLAIMER = "Synthetic data for demonstration only. Not for operational decision making."


def connect_database(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    mode = "ro" if read_only else "rw"
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode={mode}", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: Path, *, sample: bool = False) -> None:
    """Create a new database. An existing file is left intact."""
    script = SCHEMA.read_text(encoding="utf-8")
    script += "\nINSERT INTO dataset (singleton, dataset_version) VALUES (1, 'schema-only-v1');\n"
    if sample:
        script += SAMPLE.read_text(encoding="utf-8")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=False)
    try:
        with closing(connect_database(path)) as connection, connection:
            connection.executescript("BEGIN IMMEDIATE;\n" + script)
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise sqlite3.IntegrityError("Database contains broken foreign keys")
    except (OSError, sqlite3.Error):
        path.unlink()
        raise


def market_supply_trace(connection: sqlite3.Connection, shipment_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM market_supply_trace WHERE shipment_id = ? ORDER BY requirement_id, purchase_order_id",
        (shipment_id,),
    ).fetchall()
