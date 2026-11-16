"""
Phase 1 Gate 1 Comprehensive Data Integrity and Governance Test Suite.
Validates referential integrity, multi-format parity (SQLite, Parquet, CSV),
mathematical conservation, chronological consistency, and executive governance mandates.
"""

import os
import json
import sqlite3
import pytest
import pandas as pd
from typing import Set

from src.generator.config import GeneratorConfig

DB_PATH = "data/processed/control_tower.db"
PARQUET_DIR = "data/processed/parquet"
CSV_DIR = "data/processed/csv"
MANIFEST_PATH = "data/processed/dataset_manifest.json"


@pytest.fixture(scope="module")
def db_conn():
    """Provides an active connection to the SQLite control tower database."""
    assert os.path.exists(DB_PATH), f"Control tower database not found at {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


def test_manifest_structure_and_provenance():
    """
    Validates that the dataset manifest exists, contains valid metadata,
    records exactly 691 rows across 30 tables, and specifies the fixed seed 20261014.
    """
    assert os.path.exists(MANIFEST_PATH), f"Manifest file missing at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["random_seed"] == 20261014, "Manifest seed must match 20261014"
    assert data["validation_status"] == "PASSED", "Validation status must be PASSED"
    assert data["synthetic_data_flag"] is True, "Synthetic data flag must be True"
    assert "SCN-BASE" in data["scenario_coverage"]
    assert "SCN-A-API-DELAY" in data["scenario_coverage"]

    # Verify 30 tables and exactly 691 total rows
    record_counts = data["record_counts"]
    assert len(record_counts) == 30, f"Expected 30 tables in manifest, found {len(record_counts)}"
    total_records = sum(record_counts.values())
    assert total_records == 691, f"Expected 691 total records, found {total_records}"

    # Verify temporal dates in manifest
    assert data["date_range"]["history_start"] == "2024-10-28"
    assert data["date_range"]["as_of_date"] == "2026-10-26"
    assert data["date_range"]["future_end"] == "2027-04-26"


def test_multi_format_export_parity(db_conn):
    """
    Verifies that all 30 tables exported to SQLite, Parquet, and CSV
    have identical row counts, column structures, and non-empty content.
    """
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = sorted([r[0] for r in cursor.fetchall()])
    assert len(tables) == 30, f"Expected 30 SQLite tables, found {len(tables)}"

    for tbl in tables:
        df_sql = pd.read_sql_query(f"SELECT * FROM {tbl}", db_conn)
        sql_rows = len(df_sql)
        sql_cols = list(df_sql.columns)

        # 1. Parquet verification
        pq_path = os.path.join(PARQUET_DIR, f"{tbl}.parquet")
        assert os.path.exists(pq_path), f"Missing Parquet export for {tbl}"
        df_pq = pd.read_parquet(pq_path)
        assert len(df_pq) == sql_rows, f"Parquet row count mismatch on {tbl}: {len(df_pq)} vs {sql_rows}"
        assert list(df_pq.columns) == sql_cols, f"Parquet column mismatch on {tbl}"

        # 2. CSV verification
        csv_path = os.path.join(CSV_DIR, f"{tbl}.csv")
        assert os.path.exists(csv_path), f"Missing CSV export for {tbl}"
        df_csv = pd.read_csv(csv_path)
        assert len(df_csv) == sql_rows, f"CSV row count mismatch on {tbl}: {len(df_csv)} vs {sql_rows}"
        assert list(df_csv.columns) == sql_cols, f"CSV column mismatch on {tbl}"


def test_primary_key_uniqueness(db_conn):
    """
    Validates primary key uniqueness across all dimensional and fact entities.
    """
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
        "fact_inventory_lot": "lot_id",
        "fact_purchase_order": "purchase_order_id",
        "fact_production_order": "production_order_id",
        "fact_batch": "batch_id",
        "fact_quality_event": "quality_event_id",
        "fact_customer_order": "customer_order_id",
        "fact_supply_plan": "supply_plan_id",
        "fact_material_requirement": "requirement_id",
        "fact_risk_event": "risk_id",
        "fact_root_cause": "root_cause_id",
        "fact_mitigation_simulation": "simulation_id",
        "fact_recommendation": "recommendation_id"
    }
    for tbl, pk in pks.items():
        df = pd.read_sql_query(f"SELECT {pk} FROM {tbl}", db_conn)
        assert len(df) == df[pk].nunique(), f"Duplicate primary key found in {tbl}.{pk}"

    # Composite primary key uniqueness for bridge and multi-key fact tables
    composite_pks = {
        "bridge_bill_of_material": ["finished_sku_id", "material_sku_id"],
        "bridge_supplier_material": ["supplier_id", "material_sku_id"],
        "bridge_sku_market": ["finished_sku_id", "market_id"],
        "bridge_location_route": ["origin_location_id", "destination_location_id"],
        "bridge_risk_evidence": ["risk_id", "evidence_record_id"],
        "fact_demand_forecast": ["finished_sku_id", "market_id", "target_week"],
        "fact_capacity": ["production_line_id", "period_start_date"]
    }
    for tbl, cols in composite_pks.items():
        df = pd.read_sql_query(f"SELECT {', '.join(cols)} FROM {tbl}", db_conn)
        duplicates = df.duplicated(subset=cols).sum()
        assert duplicates == 0, f"Found {duplicates} duplicate composite keys in {tbl} on {cols}"


def test_master_data_referential_integrity(db_conn):
    """
    Validates complete foreign key integrity across dimensional and network bridge tables.
    """
    products = set(pd.read_sql_query("SELECT product_id FROM dim_product", db_conn)["product_id"])
    skus = set(pd.read_sql_query("SELECT finished_sku_id FROM dim_finished_sku", db_conn)["finished_sku_id"])
    materials = set(pd.read_sql_query("SELECT material_sku_id FROM dim_material", db_conn)["material_sku_id"])
    suppliers = set(pd.read_sql_query("SELECT supplier_id FROM dim_supplier", db_conn)["supplier_id"])
    locations = set(pd.read_sql_query("SELECT location_id FROM dim_location", db_conn)["location_id"])
    markets = set(pd.read_sql_query("SELECT market_id FROM dim_market", db_conn)["market_id"])

    # Finished SKU -> Product
    sku_df = pd.read_sql_query("SELECT finished_sku_id, product_id FROM dim_finished_sku", db_conn)
    assert set(sku_df["product_id"]).issubset(products), "SKU references invalid product_id"

    # Production Line -> Location
    line_df = pd.read_sql_query("SELECT production_line_id, location_id FROM dim_production_line", db_conn)
    assert set(line_df["location_id"]).issubset(locations), "Production line references invalid location_id"

    # Customer -> Market
    cust_df = pd.read_sql_query("SELECT customer_id, market_id FROM dim_customer", db_conn)
    assert set(cust_df["market_id"]).issubset(markets), "Customer references invalid market_id"

    # BOM Bridge -> Finished SKU and Material
    bom = pd.read_sql_query("SELECT finished_sku_id, material_sku_id FROM bridge_bill_of_material", db_conn)
    assert set(bom["finished_sku_id"]).issubset(skus), "BOM references invalid finished_sku_id"
    assert set(bom["material_sku_id"]).issubset(materials), "BOM references invalid material_sku_id"

    # Supplier Material Bridge -> Supplier and Material
    sm = pd.read_sql_query("SELECT supplier_id, material_sku_id FROM bridge_supplier_material", db_conn)
    assert set(sm["supplier_id"]).issubset(suppliers), "Supplier-Material references invalid supplier_id"
    assert set(sm["material_sku_id"]).issubset(materials), "Supplier-Material references invalid material_sku_id"

    # SKU Market Bridge -> SKU and Market
    smkt = pd.read_sql_query("SELECT finished_sku_id, market_id FROM bridge_sku_market", db_conn)
    assert set(smkt["finished_sku_id"]).issubset(skus), "SKU-Market references invalid finished_sku_id"
    assert set(smkt["market_id"]).issubset(markets), "SKU-Market references invalid market_id"

    # Location Route Bridge -> Origin and Destination Locations
    routes = pd.read_sql_query("SELECT origin_location_id, destination_location_id FROM bridge_location_route", db_conn)
    assert set(routes["origin_location_id"]).issubset(locations), "Route references invalid origin_location_id"
    assert set(routes["destination_location_id"]).issubset(locations), "Route references invalid destination_location_id"


def test_transactional_data_referential_integrity(db_conn):
    """
    Validates complete foreign key integrity across supply chain transaction fact tables.
    """
    skus = set(pd.read_sql_query("SELECT finished_sku_id FROM dim_finished_sku", db_conn)["finished_sku_id"])
    materials = set(pd.read_sql_query("SELECT material_sku_id FROM dim_material", db_conn)["material_sku_id"])
    suppliers = set(pd.read_sql_query("SELECT supplier_id FROM dim_supplier", db_conn)["supplier_id"])
    locations = set(pd.read_sql_query("SELECT location_id FROM dim_location", db_conn)["location_id"])
    markets = set(pd.read_sql_query("SELECT market_id FROM dim_market", db_conn)["market_id"])
    customers = set(pd.read_sql_query("SELECT customer_id FROM dim_customer", db_conn)["customer_id"])
    lines = set(pd.read_sql_query("SELECT production_line_id FROM dim_production_line", db_conn)["production_line_id"])
    prod_orders = set(pd.read_sql_query("SELECT production_order_id FROM fact_production_order", db_conn)["production_order_id"])

    # Demand History & Forecast
    dh = pd.read_sql_query("SELECT finished_sku_id, market_id FROM fact_demand_history", db_conn)
    assert set(dh["finished_sku_id"]).issubset(skus)
    assert set(dh["market_id"]).issubset(markets)

    dfc = pd.read_sql_query("SELECT finished_sku_id, market_id FROM fact_demand_forecast", db_conn)
    assert set(dfc["finished_sku_id"]).issubset(skus)
    assert set(dfc["market_id"]).issubset(markets)

    # Customer Orders
    co = pd.read_sql_query("SELECT customer_id, market_id, finished_sku_id FROM fact_customer_order", db_conn)
    assert set(co["customer_id"]).issubset(customers)
    assert set(co["market_id"]).issubset(markets)
    assert set(co["finished_sku_id"]).issubset(skus)

    # Inventory Lots (item_id can be finished SKU or material SKU)
    lots = pd.read_sql_query("SELECT item_id, location_id FROM fact_inventory_lot", db_conn)
    all_items = skus.union(materials)
    assert set(lots["item_id"]).issubset(all_items)
    assert set(lots["location_id"]).issubset(locations)

    # Purchase Orders
    po = pd.read_sql_query("SELECT supplier_id, material_sku_id FROM fact_purchase_order", db_conn)
    assert set(po["supplier_id"]).issubset(suppliers)
    assert set(po["material_sku_id"]).issubset(materials)

    # Production Orders
    prod = pd.read_sql_query("SELECT finished_sku_id, location_id, production_line_id FROM fact_production_order", db_conn)
    assert set(prod["finished_sku_id"]).issubset(skus)
    assert set(prod["location_id"]).issubset(locations)
    assert set(prod["production_line_id"]).issubset(lines)

    # Material Requirements (MRP)
    mrp = pd.read_sql_query("SELECT production_order_id, material_sku_id FROM fact_material_requirement", db_conn)
    assert set(mrp["production_order_id"]).issubset(prod_orders)
    assert set(mrp["material_sku_id"]).issubset(materials)

    # Batches
    batches = pd.read_sql_query("SELECT finished_sku_id, location_id FROM fact_batch", db_conn)
    assert set(batches["finished_sku_id"]).issubset(skus)
    assert set(batches["location_id"]).issubset(locations)

    # Capacity
    cap = pd.read_sql_query("SELECT location_id, production_line_id FROM fact_capacity", db_conn)
    assert set(cap["location_id"]).issubset(locations)
    assert set(cap["production_line_id"]).issubset(lines)

    # Shipments
    ship = pd.read_sql_query("SELECT origin_location_id, destination_location_id, finished_sku_id FROM fact_shipment", db_conn)
    assert set(ship["origin_location_id"]).issubset(locations)
    assert set(ship["destination_location_id"]).issubset(locations)
    assert set(ship["finished_sku_id"]).issubset(skus)


def test_control_tower_risk_evidence_graph_integrity(db_conn):
    """
    Validates foreign key linkages and causal graph integrity across Control Tower tables:
    fact_risk_event -> bridge_risk_evidence -> fact_root_cause ->
    fact_mitigation_simulation -> fact_recommendation.
    """
    scenarios = set(pd.read_sql_query("SELECT scenario_id FROM dim_scenario", db_conn)["scenario_id"])
    risks = pd.read_sql_query("SELECT risk_id, scenario_id FROM fact_risk_event", db_conn)
    risk_ids = set(risks["risk_id"])

    assert len(risk_ids) >= 2, "Expected at least 2 risk events for baseline Phase 1"
    assert set(risks["scenario_id"]).issubset(scenarios), "Risk references invalid scenario_id"

    # Evidence linkage
    evidence = pd.read_sql_query("SELECT risk_id, evidence_record_id FROM bridge_risk_evidence", db_conn)
    assert len(evidence) >= 5, "Expected at least 5 evidence links"
    assert set(evidence["risk_id"]).issubset(risk_ids), "Evidence references unknown risk_id"
    assert "PO-2026-001" in set(evidence["evidence_record_id"]), "Expected PO-2026-001 in evidence records"

    # Root Cause linkage
    roots = pd.read_sql_query("SELECT root_cause_id, risk_id FROM fact_root_cause", db_conn)
    assert len(roots) >= 2
    assert set(roots["risk_id"]).issubset(risk_ids), "Root cause references unknown risk_id"

    # Mitigation Simulation linkage
    sims = pd.read_sql_query("SELECT simulation_id, risk_id, scenario_id FROM fact_mitigation_simulation", db_conn)
    sim_ids = set(sims["simulation_id"])
    assert len(sims) >= 2
    assert set(sims["risk_id"]).issubset(risk_ids), "Simulation references unknown risk_id"
    assert set(sims["scenario_id"]).issubset(scenarios), "Simulation references unknown scenario_id"

    # Recommendation linkage
    recs = pd.read_sql_query("SELECT recommendation_id, risk_id, simulation_id FROM fact_recommendation", db_conn)
    assert len(recs) >= 2
    assert set(recs["risk_id"]).issubset(risk_ids), "Recommendation references unknown risk_id"
    assert set(recs["simulation_id"]).issubset(sim_ids), "Recommendation references unknown simulation_id"


def test_non_negative_and_bounded_quantities(db_conn):
    """
    Verifies mathematical bounds and non-negativity invariants across all quantitative attributes.
    """
    # 1. Demand History Exact Conservation
    dh = pd.read_sql_query("SELECT * FROM fact_demand_history", db_conn)
    assert (dh["demand_quantity"] >= 0).all()
    assert (dh["fulfilled_quantity"] >= 0).all()
    assert (dh["lost_sales_quantity"] >= 0).all()
    assert (dh["demand_quantity"] == (dh["fulfilled_quantity"] + dh["lost_sales_quantity"])).all(), \
        "Demand quantity must equal fulfilled + lost sales exactly"

    # 2. Demand Forecast P10/P90 interval geometry
    dfc = pd.read_sql_query("SELECT * FROM fact_demand_forecast", db_conn)
    assert (dfc["forecast_quantity"] >= 0).all()
    assert (dfc["lower_bound"] >= 0).all()
    assert (dfc["upper_bound"] >= dfc["lower_bound"]).all()
    assert (dfc["forecast_quantity"] >= dfc["lower_bound"]).all()
    assert (dfc["forecast_quantity"] <= dfc["upper_bound"]).all()

    # 3. Capacity Hours
    cap = pd.read_sql_query("SELECT * FROM fact_capacity", db_conn)
    assert (cap["net_available_hours"] > 0).all()
    assert (cap["committed_hours"] >= 0).all()
    assert (cap["maintenance_hours"] >= 0).all()
    assert (cap["downtime_hours"] >= 0).all()

    # 4. Inventory Lots
    lots = pd.read_sql_query("SELECT * FROM fact_inventory_lot", db_conn)
    assert (lots["quantity_on_hand"] >= 0).all()
    assert (lots["reserved_quantity"] >= 0).all()
    assert (lots["blocked_quantity"] >= 0).all()
    assert ((lots["reserved_quantity"] + lots["blocked_quantity"]) <= (lots["quantity_on_hand"] + 1e-4)).all()

    # 5. Purchase Orders
    po = pd.read_sql_query("SELECT * FROM fact_purchase_order", db_conn)
    assert (po["ordered_quantity"] > 0).all()
    assert (po["received_quantity"] >= 0).all()

    # 6. Production Orders
    prod = pd.read_sql_query("SELECT * FROM fact_production_order", db_conn)
    assert (prod["planned_quantity"] > 0).all()
    assert (prod["actual_quantity"] >= 0).all()

    # 7. Batches & Shipments
    batches = pd.read_sql_query("SELECT * FROM fact_batch", db_conn)
    assert (batches["batch_quantity"] > 0).all()

    ship = pd.read_sql_query("SELECT * FROM fact_shipment", db_conn)
    assert (ship["shipped_quantity"] > 0).all()
    assert (ship["received_quantity"] >= 0).all()


def test_temporal_and_chronological_integrity(db_conn):
    """
    Validates chronological milestone sequencing and date validity constraints.
    """
    # 1. Inventory Lots: Expiry must follow manufacture date
    lots = pd.read_sql_query("SELECT * FROM fact_inventory_lot", db_conn)
    for _, lot in lots.iterrows():
        assert lot["expiry_date"] > lot["manufacture_date"], \
            f"Expiry must follow manufacture date on {lot['lot_id']}"
        if lot["release_date"] is not None and lot["receipt_date"] is not None:
            assert str(lot["release_date"]) >= str(lot["receipt_date"]), \
                f"Release date must not precede receipt date on {lot['lot_id']}"

    # 2. Demand History vs Forecast Cutoff
    cutoff = "2026-10-26"
    dh = pd.read_sql_query("SELECT MAX(week_start_date) as max_date FROM fact_demand_history", db_conn)
    assert dh["max_date"][0] <= cutoff, f"Demand history exceeds cutoff: {dh['max_date'][0]}"

    dfc = pd.read_sql_query("SELECT MIN(target_week) as min_date FROM fact_demand_forecast", db_conn)
    assert dfc["min_date"][0] >= cutoff, f"Demand forecast target precedes cutoff: {dfc['min_date'][0]}"

    # 3. Production Orders: start date <= completion date
    prods = pd.read_sql_query("SELECT * FROM fact_production_order", db_conn)
    for _, po in prods.iterrows():
        assert po["planned_start_date"] <= po["planned_completion_date"]

    # 4. Batches: manufacture_date <= quality_submission_date <= expected_release_date
    batches = pd.read_sql_query("SELECT * FROM fact_batch", db_conn)
    for _, b in batches.iterrows():
        assert b["manufacture_date"] <= b["quality_submission_date"]
        assert b["quality_submission_date"] <= b["expected_release_date"]


def test_executive_human_approval_mandate(db_conn):
    """
    Enforces governance constraint: 100% of AI-generated mitigation recommendations
    must mandate human executive approval before execution.
    """
    recs = pd.read_sql_query("SELECT * FROM fact_recommendation", db_conn)
    assert len(recs) > 0, "Recommendations table must not be empty"

    for _, r in recs.iterrows():
        assert r["human_approval_required"] == 1 or r["human_approval_required"] is True, \
            f"Human approval required must be True on recommendation {r['recommendation_id']}"
        assert r["approval_status"] == "Pending_Review", \
            f"Initial approval status must be 'Pending_Review' on recommendation {r['recommendation_id']}"
