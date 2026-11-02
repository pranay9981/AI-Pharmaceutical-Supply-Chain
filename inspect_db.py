import sys
import sqlite3
import argparse
import pandas as pd

DB_PATH = "data/processed/control_tower.db"

def list_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("\n" + "="*60)
    print("CONTROL TOWER DATABASE TABLES (SQLite: control_tower.db)")
    print("="*60)
    print(f"{'#':<4} | {'Table Name':<35} | {'Row Count':>8}")
    print("-"*60)
    for idx, tbl in enumerate(tables, start=1):
        count = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"{idx:<4} | {tbl:<35} | {count:>8}")
    print("="*60)
    conn.close()

def view_table(table_name, limit=10):
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT {limit}", conn)
        total = pd.read_sql_query(f"SELECT COUNT(*) as cnt FROM {table_name}", conn)["cnt"][0]
        print(f"\nTABLE: {table_name} (Showing {len(df)} of {total} rows):")
        print("="*80)
        print(df.to_string(index=False))
        print("="*80)
    except Exception as e:
        print(f"Error querying table {table_name}: {e}")
    conn.close()

def run_query(sql):
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql, conn)
        print(f"\nQUERY: {sql}")
        print("="*80)
        print(df.to_string(index=False))
        print("="*80)
        print(f"Returned {len(df)} rows.")
    except Exception as e:
        print(f"SQL Error: {e}")
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect Control Tower Database")
    parser.add_argument("--list", action="store_true", help="List all tables and row counts")
    parser.add_argument("--table", type=str, help="View rows of a specific table")
    parser.add_argument("--limit", type=int, default=10, help="Max rows to display")
    parser.add_argument("--sql", type=str, help="Run a custom SQL query")
    
    args = parser.parse_args()
    
    if args.list:
        list_tables()
    elif args.table:
        view_table(args.table, args.limit)
    elif args.sql:
        run_query(args.sql)
    else:
        list_tables()

