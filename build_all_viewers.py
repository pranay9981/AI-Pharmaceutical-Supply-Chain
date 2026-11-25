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

def get_graph_data():
    nodes = [
        # Col 0: Suppliers
        {"id": "SUP-001", "name": "Deccan Active Pharma", "sub": "API Synthesis • Gujarat", "col": 0, "y": 140, "type": "SUPPLIER", "status": "APPROVED", "icon": "🏭", "table": "dim_supplier", "stage": "Stage 1: Upstream Suppliers", "desc": "Sole primary synthesizer of Amoxicillin / Clavulanate active pharmaceutical ingredient. Reliability rating: 95%."},
        {"id": "SUP-002", "name": "Western Packaging", "sub": "Packaging Converter • Pune", "col": 0, "y": 420, "type": "SUPPLIER", "status": "APPROVED", "icon": "🏭", "table": "dim_supplier", "stage": "Stage 1: Upstream Suppliers", "desc": "Secondary packaging converter supplying Alu-Alu blister foils, cartons, and bottles."},

        # Col 1: Materials
        {"id": "MAT-API-001", "name": "Amoxicillin / Clav API", "sub": "Active Chemical • 500mg", "col": 1, "y": 90, "type": "MATERIAL", "status": "CRITICAL", "icon": "🧪", "table": "dim_material", "stage": "Stage 2: Chemical Ingredients", "desc": "Active ingredient for Augmentin 500mg/125mg. 21-day supplier lead time, 540-day shelf life."},
        {"id": "MAT-EXC-001", "name": "Excipient Granules", "sub": "Binder & Disintegrant", "col": 1, "y": 210, "type": "MATERIAL", "status": "NORMAL", "icon": "🧪", "table": "dim_material", "stage": "Stage 2: Chemical Ingredients", "desc": "Microcrystalline Cellulose & Excipient Granules. Ambient storage, 720-day shelf life."},
        {"id": "MAT-PKG-BLIST", "name": "Alu-Alu Blister Foil", "sub": "Printed Foil Strip (T10)", "col": 1, "y": 330, "type": "MATERIAL", "status": "NORMAL", "icon": "📦", "table": "dim_material", "stage": "Stage 2: Packaging Components", "desc": "High-barrier printed aluminum blister foil strip for 10-tablet commercial pack."},
        {"id": "MAT-PKG-CART", "name": "Outer Carton Box", "sub": "Printed Secondary Pack", "col": 1, "y": 450, "type": "MATERIAL", "status": "CRITICAL", "icon": "📦", "table": "dim_material", "stage": "Stage 2: Packaging Components", "desc": "Secondary retail packaging carton. Subject to printing line convertor backlog."},
        {"id": "MAT-PKG-BOTT", "name": "HDPE Bottle 100cc", "sub": "Container & Closure (T30)", "col": 1, "y": 570, "type": "MATERIAL", "status": "NORMAL", "icon": "🧴", "table": "dim_material", "stage": "Stage 2: Packaging Components", "desc": "High-density polyethylene bottle with induction seal for 30-tablet institutional presentation."},

        # Col 2: Purchase Orders
        {"id": "PO-2026-001", "name": "PO-2026-001 (API)", "sub": "150 kg • Slipped +14 Days", "col": 2, "y": 90, "type": "PO", "status": "DELAYED", "icon": "📑", "table": "fact_purchase_order", "stage": "Stage 3: Procurement Contracts", "desc": "Purchase order for 150 kg API. Slipped from 2026-11-02 to 2026-11-16 (+14d) due to chromatography column breakdown."},
        {"id": "PO-2026-002", "name": "PO-2026-002 (Excip)", "sub": "200 kg • On Schedule", "col": 2, "y": 210, "type": "PO", "status": "OPEN", "icon": "📑", "table": "fact_purchase_order", "stage": "Stage 3: Procurement Contracts", "desc": "Purchase order for 200 kg excipients. On-time delivery confirmed."},
        {"id": "PO-2026-003", "name": "PO-2026-003 (Foil)", "sub": "50,000 units • In Transit", "col": 2, "y": 330, "type": "PO", "status": "OPEN", "icon": "📑", "table": "fact_purchase_order", "stage": "Stage 3: Procurement Contracts", "desc": "Alu-Alu blister foil order. In-transit via road express, on schedule."},
        {"id": "PO-2026-004", "name": "PO-2026-004 (Carton)", "sub": "40,000 units • On Schedule", "col": 2, "y": 450, "type": "PO", "status": "OPEN", "icon": "📑", "table": "fact_purchase_order", "stage": "Stage 3: Procurement Contracts", "desc": "Secondary packaging cartons. Confirmed receipt date 2026-11-05."},

        # Col 3: Manufacturing & Quality
        {"id": "PROD-2026-001", "name": "PROD-2026-001 (T10)", "sub": "20k Units • Blocked", "col": 3, "y": 100, "type": "PROD", "status": "BLOCKED", "icon": "⚙️", "table": "fact_production_order", "stage": "Stage 4: Manufacturing Cleanroom", "desc": "Cleanroom Work Order for 20,000 packs of Augmentin T10. Blocked by API raw material deficit of 47.5 kg."},
        {"id": "BATCH-AUG-2026-10", "name": "BATCH-2026-10", "sub": "15k Units • In Testing", "col": 3, "y": 230, "type": "BATCH", "status": "TESTING", "icon": "🏷️", "table": "fact_batch", "stage": "Stage 4: Manufacturing Cleanroom", "desc": "Production batch of 15,000 packs. Currently under Stage-2 Dissolution Quality Testing."},
        {"id": "QEV-2026-002", "name": "QEV-2026-002 (OOS)", "sub": "Quarantine Hold 150d", "col": 3, "y": 360, "type": "QUALITY", "status": "HOLD", "icon": "🛑", "table": "fact_quality_event", "stage": "Stage 4: cGMP Quality Deviation", "desc": "Out-of-Specification event: 20 kg API batch locked in physical quarantine hold at Plant Alpha."},
        {"id": "PROD-2026-002", "name": "PROD-2026-002 (T30)", "sub": "10k Units • Planned", "col": 3, "y": 500, "type": "PROD", "status": "PLANNED", "icon": "⚙️", "table": "fact_production_order", "stage": "Stage 4: Manufacturing Cleanroom", "desc": "Cleanroom Work Order for 10,000 bottles of Augmentin T30. Scheduled for Week 02."},

        # Col 4: Inventory Lots
        {"id": "LOT-API-2026-01", "name": "LOT-API-01", "sub": "80 kg • Released • Plant 01", "col": 4, "y": 80, "type": "LOT", "status": "AVAILABLE", "icon": "🛢️", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Lots", "desc": "Available on-hand API stock at Plant 01. Certified CoA released, expiry 2027-10-15."},
        {"id": "LOT-API-2026-02-QUAR", "name": "LOT-API-02-QUAR", "sub": "20 kg • Quarantined OOS", "col": 4, "y": 200, "type": "LOT", "status": "QUARANTINED", "icon": "🚫", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Lots", "desc": "20 kg API lot blocked under QA quarantine hold. Cannot be dispensed into production."},
        {"id": "LOT-FG-AUG-T10-26A", "name": "LOT-FG-T10-26A", "sub": "18,000 units • Exp 2028-08", "col": 4, "y": 320, "type": "LOT", "status": "RELEASED", "icon": "📦", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Lots", "desc": "Commercial finished goods lot. Available at Central DC Bhiwandi, expiry 2028-08-19."},
        {"id": "LOT-FG-AUG-T10-24X", "name": "LOT-FG-T10-24X", "sub": "3,000 units • Exp 2026-11", "col": 4, "y": 440, "type": "LOT", "status": "NEAR_EXPIRY", "icon": "⏳", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Lots", "desc": "Commercial finished goods lot near expiration. Flagged for priority FEFO dispatch to avoid scrap."},
        {"id": "LOT-FG-AUG-T30-26A", "name": "LOT-FG-T30-26A", "sub": "12,000 units • Exp 2028-09", "col": 4, "y": 560, "type": "LOT", "status": "RELEASED", "icon": "📦", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Lots", "desc": "Commercial bottle presentation lot. Stored at Bhiwandi Central DC, expiry 2028-09-09."},

        # Col 5: Finished SKUs & Central DC
        {"id": "SKU-AUG-500-T10", "name": "Augmentin T10 Strip", "sub": "10-Tablet Alu-Alu Blister", "col": 5, "y": 140, "type": "SKU", "status": "ACTIVE", "icon": "💊", "table": "dim_finished_sku", "stage": "Stage 6: Commercial Formulations", "desc": "Augmentin 500mg/125mg Tablet (Strip Pack of 10). Shelf life: 730 days. Active commercial product."},
        {"id": "LOC-DC-01", "name": "Central DC Bhiwandi", "sub": "Maharashtra Hub", "col": 5, "y": 320, "type": "DC", "status": "ACTIVE", "icon": "🏢", "table": "dim_location", "stage": "Stage 6: Central Distribution", "desc": "Primary regional distribution center in Maharashtra, supplying Hyderabad and Pune markets."},
        {"id": "SKU-AUG-500-T30", "name": "Augmentin T30 Bottle", "sub": "30-Tablet HDPE Bottle", "col": 5, "y": 520, "type": "SKU", "status": "ACTIVE", "icon": "🍾", "table": "dim_finished_sku", "stage": "Stage 6: Commercial Formulations", "desc": "Augmentin 500mg/125mg Tablet (Bottle Pack of 30). Shelf life: 730 days. Institutional supply."},

        # Col 6: Commercial Markets & Orders
        {"id": "MKT-IN-HYD", "name": "Hyderabad Market", "sub": "Telangana Health Region", "col": 6, "y": 120, "type": "MARKET", "status": "HIGH_DEMAND", "icon": "📍", "table": "dim_market", "stage": "Stage 7: Markets & Healthcare Demand", "desc": "Regional commercial territory covering Telangana hospitals and wholesale pharmacies."},
        {"id": "CUST-001", "name": "Telangana State Wholesaler", "sub": "Tier-1 Public Health", "col": 6, "y": 240, "type": "CUSTOMER", "status": "TIER1", "icon": "🏥", "table": "dim_customer", "stage": "Stage 7: Markets & Healthcare Demand", "desc": "Primary state healthcare distributor supplying over 120 community dispensaries."},
        {"id": "CUST-002", "name": "Deccan Apex Hospitals", "sub": "Institutional Network", "col": 6, "y": 360, "type": "CUSTOMER", "status": "TIER1", "icon": "🏥", "table": "dim_customer", "stage": "Stage 7: Markets & Healthcare Demand", "desc": "Tertiary multi-specialty hospital network. Strict 98% OTIF fulfillment contractual agreement."},
        {"id": "MKT-IN-PUN", "name": "Pune Market", "sub": "Maharashtra Region", "col": 6, "y": 480, "type": "MARKET", "status": "NORMAL", "icon": "📍", "table": "dim_market", "stage": "Stage 7: Markets & Healthcare Demand", "desc": "Western healthcare corridor covering Pune and adjacent secondary districts."},
        {"id": "ORD-2026-1001", "name": "ORD-1001 (Apollo/Hyd)", "sub": "1,500 Packs T10 • Open", "col": 6, "y": 600, "type": "ORDER", "status": "OPEN", "icon": "🛒", "table": "fact_customer_order", "stage": "Stage 7: Markets & Healthcare Demand", "desc": "Binding purchase order for 1,500 packs of Augmentin T10. Promised delivery date: 2026-10-30."},

        # Col 7: AI Control Tower Risk & Remediation
        {"id": "RISK-2026-001", "name": "RISK-001: API Shortage", "sub": "Score: 80.2 • Deficit: 47.5kg", "col": 7, "y": 90, "type": "RISK", "status": "HIGH_RISK", "icon": "⚠️", "table": "fact_risk_event", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Raw material stockout detected: 47.5 kg API deficit. Risk score: 80.25 (High Severity)."},
        {"id": "RISK-2026-002", "name": "RISK-002: Stockout Threat", "sub": "Score: 84.5 • Shortage: 2.4k", "col": 7, "y": 210, "type": "RISK", "status": "CRITICAL_RISK", "icon": "🚨", "table": "fact_risk_event", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Commercial stockout projected: 2,400 packs of T10 in Hyderabad. Risk score: 84.5 (Critical)."},
        {"id": "RC-2026-001", "name": "Root Cause: PO Slip", "sub": "Column Breakdown at Deccan", "col": 7, "y": 330, "type": "CAUSE", "status": "CONFIRMED", "icon": "🔍", "table": "fact_root_cause", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Forensic Causal Chain: PO-2026-001 slipped (+14d) -> Plant API Deficit -> PROD-2026-001 Blocked."},
        {"id": "REC-2026-001", "name": "REC-001: Air Expedite", "sub": "Recovers 7 Days • Cost ₹45k", "col": 7, "y": 450, "type": "REC", "status": "PENDING_APPROVAL", "icon": "✨", "table": "fact_recommendation", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Prescriptive action: Expedite PO-2026-001 via priority air freight. Cost: ₹45,000. human_approval_required = 1."},
        {"id": "REC-2026-002", "name": "REC-002: Stock Transfer", "sub": "3,000 Packs to HYD • Cost ₹18k", "col": 7, "y": 570, "type": "REC", "status": "PENDING_APPROVAL", "icon": "✨", "table": "fact_recommendation", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Emergency inventory reallocation: Transfer 3,000 packs from Pune buffer to Hyderabad. Cost: ₹18,000. human_approval_required = 1."},
    ]

    edges = [
        {"from": "SUP-001", "to": "MAT-API-001", "label": "Synthesizes", "type": "supply"},
        {"from": "SUP-001", "to": "MAT-EXC-001", "label": "Supplies", "type": "supply"},
        {"from": "SUP-002", "to": "MAT-PKG-BLIST", "label": "Converts", "type": "supply"},
        {"from": "SUP-002", "to": "MAT-PKG-CART", "label": "Converts", "type": "supply"},
        {"from": "SUP-002", "to": "MAT-PKG-BOTT", "label": "Blowmolds", "type": "supply"},
        {"from": "MAT-API-001", "to": "PO-2026-001", "label": "Procures 150kg", "type": "po"},
        {"from": "MAT-EXC-001", "to": "PO-2026-002", "label": "Procures 200kg", "type": "po"},
        {"from": "MAT-PKG-BLIST", "to": "PO-2026-003", "label": "Procures 50k", "type": "po"},
        {"from": "MAT-PKG-CART", "to": "PO-2026-004", "label": "Procures 40k", "type": "po"},
        {"from": "MAT-API-001", "to": "LOT-API-2026-01", "label": "Released Lot", "type": "inventory"},
        {"from": "MAT-API-001", "to": "LOT-API-2026-02-QUAR", "label": "Quarantined Lot", "type": "quarantine"},
        {"from": "LOT-API-2026-02-QUAR", "to": "QEV-2026-002", "label": "OOS Hold", "type": "quality"},
        {"from": "PO-2026-001", "to": "PROD-2026-001", "label": "Feed Material", "type": "blocked"},
        {"from": "PROD-2026-001", "to": "BATCH-AUG-2026-10", "label": "Produces", "type": "production"},
        {"from": "PROD-2026-001", "to": "SKU-AUG-500-T10", "label": "Fulfills", "type": "bom"},
        {"from": "PROD-2026-002", "to": "SKU-AUG-500-T30", "label": "Fulfills", "type": "bom"},
        {"from": "SKU-AUG-500-T10", "to": "LOT-FG-AUG-T10-26A", "label": "Inventory", "type": "inventory"},
        {"from": "SKU-AUG-500-T10", "to": "LOT-FG-AUG-T10-24X", "label": "Near-Expiry", "type": "risk"},
        {"from": "SKU-AUG-500-T30", "to": "LOT-FG-AUG-T30-26A", "label": "Inventory", "type": "inventory"},
        {"from": "LOT-FG-AUG-T10-26A", "to": "LOC-DC-01", "label": "Stored at", "type": "location"},
        {"from": "LOT-FG-AUG-T30-26A", "to": "LOC-DC-01", "label": "Stored at", "type": "location"},
        {"from": "LOC-DC-01", "to": "MKT-IN-HYD", "label": "Replenishes", "type": "distribution"},
        {"from": "LOC-DC-01", "to": "MKT-IN-PUN", "label": "Replenishes", "type": "distribution"},
        {"from": "MKT-IN-HYD", "to": "CUST-001", "label": "Supplies", "type": "commercial"},
        {"from": "MKT-IN-HYD", "to": "CUST-002", "label": "Supplies", "type": "commercial"},
        {"from": "CUST-002", "to": "ORD-2026-1001", "label": "Places Order", "type": "commercial"},
        {"from": "PO-2026-001", "to": "RISK-2026-001", "label": "Direct Cause", "type": "risk_cause"},
        {"from": "LOT-API-2026-02-QUAR", "to": "RISK-2026-001", "label": "Contributing Factor", "type": "risk_factor"},
        {"from": "RISK-2026-001", "to": "PROD-2026-001", "label": "Production Impact", "type": "risk_impact"},
        {"from": "PROD-2026-001", "to": "RISK-2026-002", "label": "Downstream Stockout", "type": "risk_cascade"},
        {"from": "RISK-2026-001", "to": "RC-2026-001", "label": "Causal Trace", "type": "causal"},
        {"from": "RC-2026-001", "to": "REC-2026-001", "label": "Mitigation Strategy", "type": "mitigation"},
        {"from": "RISK-2026-002", "to": "REC-2026-002", "label": "Stock Reallocation", "type": "mitigation"},
    ]

    return {"nodes": nodes, "edges": edges}

print("Loaded all data.")
