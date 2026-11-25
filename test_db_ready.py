import sqlite3
import json
import os

DB_PATH = 'data/processed/control_tower.db'

def get_db_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]

    db_dict = {}

    for tname in tables:
        cols_info = cursor.execute(f"PRAGMA table_info({tname})").fetchall()
        columns = []
        for c in cols_info:
            columns.append({
                "cid": c[0],
                "name": c[1],
                "type": c[2],
                "notnull": bool(c[3]),
                "dflt_value": c[4],
                "pk": bool(c[5])
            })
        col_names = [c["name"] for c in columns]
        rows = cursor.execute(f"SELECT * FROM {tname}").fetchall()
        sql_res = cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tname}'").fetchone()
        sql = sql_res[0] if sql_res else ""

        if tname.startswith('dim_'):
            tier = "Tier 1: Master Dimensions"
            tier_short = "T1"
        elif tname.startswith('bridge_'):
            tier = "Tier 2: Network Topology Bridges"
            tier_short = "T2"
        elif tname in ['fact_risk_event', 'fact_root_cause', 'fact_mitigation_simulation', 'fact_recommendation']:
            tier = "Tier 4: Risk & Decision Engine Facts"
            tier_short = "T4"
        else:
            tier = "Tier 3: Transactional Facts"
            tier_short = "T3"

        db_dict[tname] = {
            "name": tname,
            "tier": tier,
            "tier_short": tier_short,
            "sql": sql,
            "columns": columns,
            "col_names": col_names,
            "rows": rows,
            "row_count": len(rows)
        }

    conn.close()
    return db_dict

print("DB data helper ready.")
