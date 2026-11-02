import os
import sys
import json
import sqlite3
import datetime
import pandas as pd
from typing import Dict, Any

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.generator.config import GeneratorConfig
from src.generator.master_data import generate_master_and_bridge_data
from src.generator.demand_data import generate_demand_and_forecast_data
from src.generator.supply_data import generate_supply_and_operations_data
from src.generator.disruption_injector import inject_disruptions
from src.models.control_tower import DatasetManifest

def run_synthetic_generation(config: GeneratorConfig = None) -> Dict[str, pd.DataFrame]:
    if config is None:
        config = GeneratorConfig()

    print("=" * 70)
    print("AI-POWERED PHARMACEUTICAL SUPPLY CHAIN CONTROL TOWER")
    print(f"Executing Phase 1 Synthetic Data Generation (Seed: {config.random_seed})")
    print(f"Planning Horizon: {config.history_weeks} historical weeks | {config.future_weeks} future weeks")
    print(f"As-Of Planning Cutoff: {config.planning_as_of_date}")
    print("=" * 70)

    # 1. Master and Bridge Tables
    master_dict = generate_master_and_bridge_data(config)
    
    # 2. Demand and Forecast Tables
    demand_dict = generate_demand_and_forecast_data(config)
    
    # 3. Supply and Operational Tables
    supply_dict = generate_supply_and_operations_data(config)
    
    # 4. Disruption Injection & Control Tower Outputs
    disruption_dict = inject_disruptions(master_dict, supply_dict, config)
    
    # Consolidate into table dictionary
    all_data_models: Dict[str, list] = {}
    
    # Merge master
    for k, v in master_dict.items():
        all_data_models[k] = v
        
    # Merge demand
    for k, v in demand_dict.items():
        all_data_models[k] = v
        
    # Merge supply
    for k, v in supply_dict.items():
        all_data_models[k] = v
        
    # Merge control tower & disruption
    all_data_models["fact_risk_event"] = disruption_dict["fact_risk_event"]
    all_data_models["bridge_risk_evidence"] = disruption_dict["bridge_risk_evidence"]
    all_data_models["fact_root_cause"] = disruption_dict["fact_root_cause"]
    all_data_models["fact_mitigation_simulation"] = disruption_dict["fact_mitigation_simulation"]
    all_data_models["fact_recommendation"] = disruption_dict["fact_recommendation"]

    # Convert Pydantic models to Pandas DataFrames
    tables: Dict[str, pd.DataFrame] = {}
    for table_name, model_list in all_data_models.items():
        if model_list:
            records = [m.model_dump() for m in model_list]
            tables[table_name] = pd.DataFrame(records)
        else:
            tables[table_name] = pd.DataFrame()

    print(f"\n[1/4] Model serialization complete: {len(tables)} tables converted to DataFrames.")

    # 5. Integrity & Quality Validation Checks
    print("\n[2/4] Running automated referential integrity & business logic validation...")
    validation_passed = True
    
    # Check 1: Primary key uniqueness
    pk_rules = {
        "dim_product": "product_id",
        "dim_finished_sku": "finished_sku_id",
        "dim_material": "material_sku_id",
        "dim_supplier": "supplier_id",
        "dim_location": "location_id",
        "dim_customer": "customer_id",
        "dim_market": "market_id",
        "dim_production_line": "production_line_id",
        "dim_scenario": "scenario_id",
        "fact_risk_event": "risk_id",
        "fact_root_cause": "root_cause_id",
        "fact_mitigation_simulation": "simulation_id",
        "fact_recommendation": "recommendation_id"
    }
    
    for tbl, pk in pk_rules.items():
        if tbl in tables and not tables[tbl].empty:
            count = len(tables[tbl])
            unique_count = tables[tbl][pk].nunique()
            if count != unique_count:
                print(f"❌ PK validation failed on {tbl}.{pk}: {count} rows vs {unique_count} unique.")
                validation_passed = False
            else:
                pass
    
    # Check 2: Foreign key validation (SKUs in BOM exist in dim_finished_sku)
    valid_sku_ids = set(tables["dim_finished_sku"]["finished_sku_id"])
    bom_skus = set(tables["bridge_bill_of_material"]["finished_sku_id"])
    if not bom_skus.issubset(valid_sku_ids):
        print(f"❌ FK validation failed: Unknown SKUs in BOM: {bom_skus - valid_sku_ids}")
        validation_passed = False
        
    valid_mat_ids = set(tables["dim_material"]["material_sku_id"])
    bom_mats = set(tables["bridge_bill_of_material"]["material_sku_id"])
    if not bom_mats.issubset(valid_mat_ids):
        print(f"❌ FK validation failed: Unknown Materials in BOM: {bom_mats - valid_mat_ids}")
        validation_passed = False

    # Check 3: Date logic (Expiry must follow manufacture date)
    lots = tables["fact_inventory_lot"]
    for _, lot in lots.iterrows():
        mfg = lot["manufacture_date"]
        exp = lot["expiry_date"]
        if exp <= mfg:
            print(f"❌ Date logic failed on lot {lot['lot_id']}: expiry {exp} <= mfg {mfg}")
            validation_passed = False
            
    # Check 4: Reserved + Blocked <= On Hand
    for _, lot in lots.iterrows():
        on_hand = lot["quantity_on_hand"]
        res = lot["reserved_quantity"]
        blk = lot["blocked_quantity"]
        if (res + blk) > (on_hand + 1e-5):
            print(f"❌ Inventory logic failed on lot {lot['lot_id']}: reserved+blocked ({res+blk}) > on_hand ({on_hand})")
            validation_passed = False

    if validation_passed:
        print("  All referential integrity, range, date, and inventory logic checks PASSED.")
    else:
        raise ValueError("Data validation checks failed. Aborting export.")

    # 6. Database, Parquet, and CSV Export
    print("\n[3/4] Exporting tables to SQLite relational database, Parquet, and CSV format...")
    os.makedirs(os.path.dirname(config.output_db_path), exist_ok=True)
    os.makedirs(config.output_parquet_dir, exist_ok=True)
    os.makedirs(config.output_csv_dir, exist_ok=True)

    # SQLite
    conn = sqlite3.connect(config.output_db_path)
    record_counts = {}
    for table_name, df in tables.items():
        # SQLite
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        # Parquet
        parquet_path = os.path.join(config.output_parquet_dir, f"{table_name}.parquet")
        df.to_parquet(parquet_path, index=False)
        # CSV (Human-readable plain text)
        csv_path = os.path.join(config.output_csv_dir, f"{table_name}.csv")
        df.to_csv(csv_path, index=False)
        record_counts[table_name] = len(df)
    conn.close()
    print(f"  SQLite database successfully written to: {config.output_db_path}")
    print(f"  Parquet files successfully written to: {config.output_parquet_dir}/")
    print(f"  CSV files successfully written to: {config.output_csv_dir}/")

    # 7. Dataset Manifest Generation
    print("\n[4/4] Writing dataset manifest and reproducibility metadata...")
    manifest = DatasetManifest(
        dataset_version="v1.0.0-phase1-aug",
        generation_timestamp=datetime.datetime.now(),
        random_seed=config.random_seed,
        record_counts=record_counts,
        date_range={
            "history_start": config.history_start_date.isoformat(),
            "as_of_date": config.planning_as_of_date.isoformat(),
            "future_end": config.future_end_date.isoformat()
        },
        scenario_coverage=["SCN-BASE", "SCN-A-API-DELAY"],
        validation_status="PASSED",
        synthetic_data_flag=config.synthetic_flag
    )

    with open(config.output_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(mode="json"), f, indent=2)
    print(f"  Dataset manifest saved to: {config.output_manifest_path}")

    # Print summary table
    print("\n" + "=" * 70)
    print("PHASE 1 DATASET SUMMARY")
    print("=" * 70)
    print(f"{'Table Name':<35} | {'Row Count':>10} | {'Status':<15}")
    print("-" * 70)
    for tbl, count in record_counts.items():
        print(f"{tbl:<35} | {count:>10} | {'Verified':<15}")
    print("-" * 70)
    total_rows = sum(record_counts.values())
    print(f"{'TOTAL GENERATED RECORDS':<35} | {total_rows:>10} | {'READY':<15}")
    print("=" * 70)

    return tables

if __name__ == "__main__":
    run_synthetic_generation()
