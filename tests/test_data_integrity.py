import os
import sqlite3
import pytest
import pandas as pd
from src.generator.config import GeneratorConfig

DB_PATH = "data/processed/control_tower.db"

@pytest.fixture(scope="module")
def db_conn():
    assert os.path.exists(DB_PATH), f"Database not found at {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()

def test_manifest_exists():
    import json
    manifest_path = "data/processed/dataset_manifest.json"
    assert os.path.exists(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["random_seed"] == 20261014
    assert data["validation_status"] == "PASSED"
    assert "SCN-A-API-DELAY" in data["scenario_coverage"]

def test_primary_key_uniqueness(db_conn):
    pks = {
        "dim_product": "product_id",
        "dim_finished_sku": "finished_sku_id",
        "dim_material": "material_sku_id",
        "dim_supplier": "supplier_id",
        "dim_location": "location_id",
        "dim_market": "market_id",
        "dim_customer": "customer_id",
        "dim_production_line": "production_line_id",
        "dim_scenario": "scenario_id",
        "fact_risk_event": "risk_id",
        "fact_root_cause": "root_cause_id",
        "fact_mitigation_simulation": "simulation_id",
        "fact_recommendation": "recommendation_id"
    }
    for tbl, pk in pks.items():
        df = pd.read_sql_query(f"SELECT {pk} FROM {tbl}", db_conn)
        assert len(df) == df[pk].nunique(), f"Duplicate PK found in {tbl}.{pk}"

def test_bom_referential_integrity(db_conn):
    skus = set(pd.read_sql_query("SELECT finished_sku_id FROM dim_finished_sku", db_conn)["finished_sku_id"])
    mats = set(pd.read_sql_query("SELECT material_sku_id FROM dim_material", db_conn)["material_sku_id"])
    bom = pd.read_sql_query("SELECT finished_sku_id, material_sku_id FROM bridge_bill_of_material", db_conn)
    
    for _, row in bom.iterrows():
        assert row["finished_sku_id"] in skus, f"BOM references invalid SKU: {row['finished_sku_id']}"
        assert row["material_sku_id"] in mats, f"BOM references invalid Material: {row['material_sku_id']}"

def test_inventory_lot_eligibility_logic(db_conn):
    lots = pd.read_sql_query("SELECT * FROM fact_inventory_lot", db_conn)
    for _, lot in lots.iterrows():
        # Expiry must follow manufacture date
        assert lot["expiry_date"] > lot["manufacture_date"], f"Expiry must be after mfg date on {lot['lot_id']}"
        # Reserved + Blocked <= On Hand
        assert (lot["reserved_quantity"] + lot["blocked_quantity"]) <= (lot["quantity_on_hand"] + 1e-4), \
            f"Reserved + Blocked exceeds On-Hand on {lot['lot_id']}"

def test_disruption_scenario_linkage(db_conn):
    risks = pd.read_sql_query("SELECT * FROM fact_risk_event WHERE scenario_id = 'SCN-A-API-DELAY'", db_conn)
    assert len(risks) >= 2, "Expected at least 2 risk alerts for Scenario A (Material Shortage + Stockout)"
    
    evidence = pd.read_sql_query("SELECT * FROM bridge_risk_evidence", db_conn)
    assert len(evidence) > 0, "Expected linked evidence records"
    assert "PO-2026-001" in set(evidence["evidence_record_id"]), "Expected PO-2026-001 cited as direct cause"

def test_demand_history_and_forecast_continuity(db_conn):
    history = pd.read_sql_query("SELECT COUNT(DISTINCT week_start_date) as cnt FROM fact_demand_history", db_conn)
    assert history["cnt"][0] == 104, f"Expected 104 historical weeks, found {history['cnt'][0]}"
    
    forecast = pd.read_sql_query("SELECT COUNT(DISTINCT target_week) as cnt FROM fact_demand_forecast", db_conn)
    assert forecast["cnt"][0] == 26, f"Expected 26 forecast weeks, found {forecast['cnt'][0]}"

def test_mitigation_human_approval_mandate(db_conn):
    recs = pd.read_sql_query("SELECT * FROM fact_recommendation", db_conn)
    assert len(recs) > 0
    for _, r in recs.iterrows():
        assert r["human_approval_required"] == 1 or r["human_approval_required"] is True, \
            "Human approval required mandate must be True"
        assert r["approval_status"] == "Pending_Review", "Initial recommendation status must be Pending_Review"

