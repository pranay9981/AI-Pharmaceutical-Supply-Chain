import json
import os
import shutil

# 1. Complete 34 Nodes
nodes = [
    # Col 0: Origins (x=60)
    {"id": "SUP-001", "name": "Deccan Active Pharma", "sub": "API Synthesizer • Gujarat", "col": 0, "y": 100, "w": 180, "h": 72, "type": "SUPPLIER", "status": "APPROVED", "icon": "🏭", "table": "dim_supplier", "stage": "Stage 1: Upstream Sourcing", "desc": "Sole primary synthesizer of Amoxicillin / Clavulanate active pharmaceutical ingredient. Contract lead time: 21 days."},
    {"id": "SUP-002", "name": "Western Packaging", "sub": "Packaging Converter • Pune", "col": 0, "y": 320, "w": 180, "h": 72, "type": "SUPPLIER", "status": "APPROVED", "icon": "🏭", "table": "dim_supplier", "stage": "Stage 1: Upstream Sourcing", "desc": "Secondary packaging converter supplying printed cartons, blister foils, and HDPE bottles."},
    {"id": "LINE-PLANT1-01", "name": "Line 1 Granulation", "sub": "Capacity: 100 hrs/wk • Baddi", "col": 0, "y": 540, "w": 180, "h": 72, "type": "LINE", "status": "ACTIVE", "icon": "⚙️", "table": "dim_production_line", "stage": "Stage 1: Manufacturing Facility", "desc": "High-speed cleanroom granulation & compression line. Scheduled Sunday CIP maintenance."},

    # Col 1: Materials (x=280)
    {"id": "MAT-API-001", "name": "Amoxicillin / Clav API", "sub": "Active Chemical • 500/125mg", "col": 1, "y": 80, "w": 180, "h": 72, "type": "MATERIAL", "status": "CRITICAL", "icon": "🧪", "table": "dim_material", "stage": "Stage 2: Chemical & Packaging Materials", "desc": "Active pharmaceutical ingredient for Augmentin 500mg. 21-day supplier lead time."},
    {"id": "MAT-EXC-001", "name": "Excipient Granules", "sub": "Microcrystalline Cellulose", "col": 1, "y": 180, "w": 180, "h": 72, "type": "MATERIAL", "status": "NORMAL", "icon": "🧪", "table": "dim_material", "stage": "Stage 2: Chemical & Packaging Materials", "desc": "Binder & disintegrant excipient granules for tablet formulation. Ambient storage condition."},
    {"id": "MAT-PKG-BLIST", "name": "Alu-Alu Blister Foil", "sub": "Printed Barrier Foil Strip", "col": 1, "y": 280, "w": 180, "h": 72, "type": "MATERIAL", "status": "NORMAL", "icon": "📦", "table": "dim_material", "stage": "Stage 2: Chemical & Packaging Materials", "desc": "High-barrier printed aluminum foil strip for 10-tablet commercial blister presentation."},
    {"id": "MAT-PKG-CART", "name": "Printed Outer Cartons", "sub": "Secondary Unit Carton Box", "col": 1, "y": 380, "w": 180, "h": 72, "type": "MATERIAL", "status": "CRITICAL", "icon": "📦", "table": "dim_material", "stage": "Stage 2: Chemical & Packaging Materials", "desc": "Shared retail outer carton packaging box. Essential for both T10 strips and T30 bottles."},
    {"id": "MAT-PKG-BOTT", "name": "HDPE Bottle 100cc", "sub": "Container & Closure (T30)", "col": 1, "y": 480, "w": 180, "h": 72, "type": "MATERIAL", "status": "NORMAL", "icon": "🧴", "table": "dim_material", "stage": "Stage 2: Chemical & Packaging Materials", "desc": "High-density polyethylene bottle for institutional 30-tablet presentation."},

    # Col 2: Procurement Contracts (x=500)
    {"id": "PO-2026-001", "name": "PO-2026-001 (API)", "sub": "150 kg • Slipped +14 Days", "col": 2, "y": 80, "w": 180, "h": 72, "type": "PO", "status": "DELAYED", "icon": "📑", "table": "fact_purchase_order", "stage": "Stage 3: Procurement Contracts", "desc": "Purchase order for 150 kg API. Slipped from Nov 02 to Nov 16 due to column breakdown at Deccan."},
    {"id": "PO-2026-002", "name": "PO-2026-002 (Excip)", "sub": "200 kg • On Schedule", "col": 2, "y": 180, "w": 180, "h": 72, "type": "PO", "status": "OPEN", "icon": "📑", "table": "fact_purchase_order", "stage": "Stage 3: Procurement Contracts", "desc": "Purchase order for 200 kg excipients. Confirmed on schedule by supplier."},
    {"id": "PO-2026-003", "name": "PO-2026-003 (Foil)", "sub": "50,000 units • In Transit", "col": 2, "y": 280, "w": 180, "h": 72, "type": "PO", "status": "OPEN", "icon": "📑", "table": "fact_purchase_order", "stage": "Stage 3: Procurement Contracts", "desc": "Blister foil order. In-transit via road logistics, scheduled arrival on track."},
    {"id": "PO-2026-004", "name": "PO-2026-004 (Carton)", "sub": "40,000 units • Converter Delay", "col": 2, "y": 380, "w": 180, "h": 72, "type": "PO", "status": "DELAYED", "icon": "📑", "table": "fact_purchase_order", "stage": "Stage 3: Procurement Contracts", "desc": "Outer carton order with Western Packaging. Converter press delay bottlenecks both T10 and T30 lines."},

    # Col 3: Manufacturing Orders & Quality Batches (x=720)
    {"id": "PROD-2026-001", "name": "Work Order PROD-001", "sub": "Augmentin T10 • 20k Packs", "col": 3, "y": 100, "w": 180, "h": 72, "type": "PROD", "status": "BLOCKED", "icon": "⚙️", "table": "fact_production_order", "stage": "Stage 4: Manufacturing Shopfloor", "desc": "Cleanroom Work Order for 20,000 packs of Augmentin T10. Blocked by API deficit of 47.5 kg."},
    {"id": "BATCH-AUG-2026-10", "name": "Batch 10 (In Testing)", "sub": "15k Units • Dissolution Check", "col": 3, "y": 240, "w": 180, "h": 72, "type": "BATCH", "status": "TESTING", "icon": "🏷️", "table": "fact_batch", "stage": "Stage 4: Manufacturing Shopfloor", "desc": "Compressed batch of 15,000 packs under QA testing. Fails stage-2 dissolution threshold."},
    {"id": "QEV-2026-002", "name": "Quality Deviation OOS", "sub": "Quarantine Hold (150 Days)", "col": 3, "y": 380, "w": 180, "h": 72, "type": "QUALITY", "status": "HOLD", "icon": "🛑", "table": "fact_quality_event", "stage": "Stage 4: cGMP Quality Assurance", "desc": "Out-of-Specification event logged by QA Director. Lot placed in physical quarantine hold."},
    {"id": "PROD-2026-002", "name": "Work Order PROD-002", "sub": "Augmentin T30 • 10k Bottles", "col": 3, "y": 520, "w": 180, "h": 72, "type": "PROD", "status": "PLANNED", "icon": "⚙️", "table": "fact_production_order", "stage": "Stage 4: Manufacturing Shopfloor", "desc": "Cleanroom Work Order for 10,000 bottles of Augmentin T30. Blocked in Scenario C by carton shortage."},

    # Col 4: Inventory Lots (Raw & FG) (x=940)
    {"id": "LOT-API-2026-01", "name": "LOT-API-01 (Released)", "sub": "80 kg API • Plant Alpha", "col": 4, "y": 80, "w": 180, "h": 72, "type": "LOT", "status": "AVAILABLE", "icon": "🛢️", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Warehousing", "desc": "Certified active API on hand at Plant Alpha. CoA released, consumed by initial production runs."},
    {"id": "LOT-API-2026-02-QUAR", "name": "LOT-API-02 (Quarantine)", "sub": "20 kg API • Locked OOS", "col": 4, "y": 200, "w": 180, "h": 72, "type": "LOT", "status": "QUARANTINED", "icon": "🚫", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Warehousing", "desc": "20 kg API lot blocked under QA quarantine hold. Cannot be dispensed into production."},
    {"id": "LOT-FG-AUG-T10-26A", "name": "LOT-FG-T10-26A", "sub": "18,000 packs • Exp 2028-08", "col": 4, "y": 320, "w": 180, "h": 72, "type": "LOT", "status": "RELEASED", "icon": "📦", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Warehousing", "desc": "Commercial finished goods lot. Available at Bhiwandi Central DC, expiry 2028-08-19."},
    {"id": "LOT-FG-AUG-T10-24X", "name": "LOT-FG-T10-24X (Sub-MARSL)", "sub": "3,000 packs • Exp 2026-11", "col": 4, "y": 440, "w": 180, "h": 72, "type": "LOT", "status": "NEAR_EXPIRY", "icon": "⏳", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Warehousing", "desc": "Commercial finished goods lot near expiration (<90d). Rejected by hospital contract MARSL gate."},
    {"id": "LOT-FG-AUG-T30-26A", "name": "LOT-FG-T30-26A", "sub": "12,000 bottles • Exp 2028-09", "col": 4, "y": 560, "w": 180, "h": 72, "type": "LOT", "status": "RELEASED", "icon": "📦", "table": "fact_inventory_lot", "stage": "Stage 5: FEFO Inventory Warehousing", "desc": "Commercial bottle presentation lot. Stored at Bhiwandi Central DC, expiry 2028-09-09."},

    # Col 5: Finished SKUs & Central Distribution (x=1160)
    {"id": "SKU-AUG-500-T10", "name": "Augmentin T10 Strip", "sub": "10-Tablet Alu-Alu Blister", "col": 5, "y": 140, "w": 180, "h": 72, "type": "SKU", "status": "ACTIVE", "icon": "💊", "table": "dim_finished_sku", "stage": "Stage 6: Commercial SKUs & Distribution", "desc": "Augmentin 500mg/125mg Tablet (Strip Pack of 10). Shelf life: 730 days. Fast-moving SKU."},
    {"id": "LOC-DC-01", "name": "Central DC Bhiwandi", "sub": "Maharashtra Hub", "col": 5, "y": 320, "w": 180, "h": 72, "type": "DC", "status": "ACTIVE", "icon": "🏢", "table": "dim_location", "stage": "Stage 6: Commercial SKUs & Distribution", "desc": "Primary regional distribution center in Maharashtra, supplying Hyderabad and Pune markets."},
    {"id": "SKU-AUG-500-T30", "name": "Augmentin T30 Bottle", "sub": "30-Tablet HDPE Bottle", "col": 5, "y": 520, "w": 180, "h": 72, "type": "SKU", "status": "ACTIVE", "icon": "🍾", "table": "dim_finished_sku", "stage": "Stage 6: Commercial SKUs & Distribution", "desc": "Augmentin 500mg/125mg Tablet (Bottle Pack of 30). Shelf life: 730 days. Institutional presentation."},

    # Col 6: Markets, Customers & Orders (x=1380)
    {"id": "MKT-IN-HYD", "name": "Hyderabad Market", "sub": "Telangana Health Region", "col": 6, "y": 100, "w": 180, "h": 72, "type": "MARKET", "status": "HIGH_DEMAND", "icon": "📍", "table": "dim_market", "stage": "Stage 7: Healthcare Demand & Orders", "desc": "Regional commercial territory covering Telangana hospitals and wholesale pharmacies."},
    {"id": "CUST-001", "name": "Telangana Wholesaler", "sub": "Tier-1 Public Health", "col": 6, "y": 220, "w": 180, "h": 72, "type": "CUSTOMER", "status": "TIER1", "icon": "🏥", "table": "dim_customer", "stage": "Stage 7: Healthcare Demand & Orders", "desc": "Primary state healthcare distributor supplying over 120 community dispensaries."},
    {"id": "CUST-002", "name": "Deccan Apex Hospitals", "sub": "Institutional Network", "col": 6, "y": 340, "w": 180, "h": 72, "type": "CUSTOMER", "status": "TIER1", "icon": "🏥", "table": "dim_customer", "stage": "Stage 7: Healthcare Demand & Orders", "desc": "Tertiary multi-specialty hospital network. Enforces 90-day MARSL shelf life gate."},
    {"id": "MKT-IN-PUN", "name": "Pune Market", "sub": "Maharashtra Region", "col": 6, "y": 460, "w": 180, "h": 72, "type": "MARKET", "status": "NORMAL", "icon": "📍", "table": "dim_market", "stage": "Stage 7: Healthcare Demand & Orders", "desc": "Western healthcare corridor covering Pune and adjacent secondary health districts."},
    {"id": "ORD-2026-1001", "name": "Apollo Hospital Order", "sub": "1,500 Packs T10 • Critical", "col": 6, "y": 580, "w": 180, "h": 72, "type": "ORDER", "status": "OPEN", "icon": "🛒", "table": "fact_customer_order", "stage": "Stage 7: Healthcare Demand & Orders", "desc": "Binding purchase order for 1,500 packs of Augmentin T10. Promised delivery date: 2026-10-30."},

    # Col 7: AI Control Tower Risk & Remediation (x=1600)
    {"id": "RISK-2026-001", "name": "RISK-001: Material Deficit", "sub": "Score: 80.2 • Deficit: 47.5kg", "col": 7, "y": 90, "w": 180, "h": 72, "type": "RISK", "status": "HIGH_RISK", "icon": "⚠️", "table": "fact_risk_event", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Raw material stockout detected: 47.5 kg API deficit. Risk score: 80.25 (High Severity)."},
    {"id": "RISK-2026-002", "name": "RISK-002: Stockout Threat", "sub": "Score: 84.5 • Shortage: 2.4k", "col": 7, "y": 210, "w": 180, "h": 72, "type": "RISK", "status": "CRITICAL_RISK", "icon": "🚨", "table": "fact_risk_event", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Commercial stockout projected: 2,400 packs of T10 in Hyderabad. Risk score: 84.5 (Critical)."},
    {"id": "RC-2026-001", "name": "Root Cause: PO Slip", "sub": "Column Breakdown at Deccan", "col": 7, "y": 330, "w": 180, "h": 72, "type": "CAUSE", "status": "CONFIRMED", "icon": "🔍", "table": "fact_root_cause", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Forensic Causal Chain: PO-2026-001 slipped (+14d) -> Plant API Deficit -> PROD-2026-001 Blocked."},
    {"id": "REC-2026-001", "name": "REC-001: Air Expedite", "sub": "Recovers 7 Days • Cost ₹45k", "col": 7, "y": 450, "w": 180, "h": 72, "type": "REC", "status": "PENDING_APPROVAL", "icon": "✨", "table": "fact_recommendation", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Prescriptive action: Expedite PO-2026-001 via priority air freight. Cost: ₹45,000. human_approval_required = 1."},
    {"id": "REC-2026-002", "name": "REC-002: Stock Transfer", "sub": "3,000 Packs to HYD • Cost ₹18k", "col": 7, "y": 570, "w": 180, "h": 72, "type": "REC", "status": "PENDING_APPROVAL", "icon": "✨", "table": "fact_recommendation", "stage": "Stage 8: Autonomous Control Tower AI", "desc": "Emergency inventory reallocation: Transfer 3,000 packs from Pune buffer to Hyderabad. Cost: ₹18,000. human_approval_required = 1."}
]

# Set explicit coordinates
for n in nodes:
    n['x'] = n['col'] * 220 + 60

# 2. Complete 50 Connected Edges
edges = [
    # 1. Stage 1 (Origins) to Stage 2 (Materials) & Facility to Work Orders
    {"from": "SUP-001", "to": "MAT-API-001", "label": "Synthesizes API"},
    {"from": "SUP-001", "to": "MAT-EXC-001", "label": "Supplies Excipient"},
    {"from": "SUP-002", "to": "MAT-PKG-BLIST", "label": "Converts Foil"},
    {"from": "SUP-002", "to": "MAT-PKG-CART", "label": "Converts Cartons"},
    {"from": "SUP-002", "to": "MAT-PKG-BOTT", "label": "Blowmolds Bottles"},
    {"from": "LINE-PLANT1-01", "to": "PROD-2026-001", "label": "Granulates T10 Strips"},
    {"from": "LINE-PLANT1-01", "to": "PROD-2026-002", "label": "Compresses T30 Bottles"},

    # 2. Materials to Purchase Orders & Plant Stock
    {"from": "MAT-API-001", "to": "PO-2026-001", "label": "Procures 150kg API"},
    {"from": "MAT-EXC-001", "to": "PO-2026-002", "label": "Procures 200kg Excipient"},
    {"from": "MAT-PKG-BLIST", "to": "PO-2026-003", "label": "Procures 50k Foils"},
    {"from": "MAT-PKG-CART", "to": "PO-2026-004", "label": "Procures 40k Cartons"},
    {"from": "MAT-PKG-BOTT", "to": "PROD-2026-002", "label": "Feeds Bottle Line"},
    {"from": "MAT-API-001", "to": "LOT-API-2026-01", "label": "Released Plant Stock"},
    {"from": "MAT-API-001", "to": "LOT-API-2026-02-QUAR", "label": "Quarantined OOS Stock"},

    # 3. Purchase Orders & Plant Lots to Work Orders
    {"from": "PO-2026-001", "to": "PROD-2026-001", "label": "Feeds API Batch (Delayed)"},
    {"from": "PO-2026-002", "to": "PROD-2026-001", "label": "Feeds Excipients"},
    {"from": "PO-2026-003", "to": "PROD-2026-001", "label": "Feeds Blister Foil"},
    {"from": "PO-2026-004", "to": "PROD-2026-001", "label": "Feeds T10 Cartons"},
    {"from": "PO-2026-004", "to": "PROD-2026-002", "label": "Feeds T30 Cartons"},
    {"from": "LOT-API-2026-01", "to": "PROD-2026-001", "label": "Feeds Cleanroom Line"},

    # 4. Work Orders to Batches, Quality Events, and Finished SKUs
    {"from": "PROD-2026-001", "to": "BATCH-AUG-2026-10", "label": "Compresses Batch 10"},
    {"from": "BATCH-AUG-2026-10", "to": "QEV-2026-002", "label": "Fails Dissolution Test"},
    {"from": "QEV-2026-002", "to": "LOT-API-2026-02-QUAR", "label": "Quarantines Active Lot"},
    {"from": "PROD-2026-001", "to": "SKU-AUG-500-T10", "label": "Fulfills Finished T10"},
    {"from": "PROD-2026-002", "to": "SKU-AUG-500-T30", "label": "Fulfills Finished T30"},

    # 5. Finished SKUs to Finished Lots & Central DC
    {"from": "SKU-AUG-500-T10", "to": "LOT-FG-AUG-T10-26A", "label": "Commercial Lot (Exp 2028)"},
    {"from": "SKU-AUG-500-T10", "to": "LOT-FG-AUG-T10-24X", "label": "Near-Expiry Lot (<90d)"},
    {"from": "SKU-AUG-500-T30", "to": "LOT-FG-AUG-T30-26A", "label": "Commercial Bottle Lot"},
    {"from": "LOT-FG-AUG-T10-26A", "to": "LOC-DC-01", "label": "Stored at Central DC"},
    {"from": "LOT-FG-AUG-T10-24X", "to": "LOC-DC-01", "label": "Stored at Central DC"},
    {"from": "LOT-FG-AUG-T30-26A", "to": "LOC-DC-01", "label": "Stored at Central DC"},
    {"from": "SKU-AUG-500-T10", "to": "LOC-DC-01", "label": "DC Inventory Allocation"},
    {"from": "SKU-AUG-500-T30", "to": "LOC-DC-01", "label": "DC Inventory Allocation"},

    # 6. Central DC to Regional Markets & Risk
    {"from": "LOC-DC-01", "to": "MKT-IN-HYD", "label": "Replenishes Hyderabad"},
    {"from": "LOC-DC-01", "to": "MKT-IN-PUN", "label": "Replenishes Pune"},
    {"from": "LOC-DC-01", "to": "RISK-2026-001", "label": "Depletes Safety Buffer"},

    # 7. Markets to Customers & Customer Orders
    {"from": "MKT-IN-HYD", "to": "CUST-001", "label": "Supplies Wholesalers"},
    {"from": "MKT-IN-HYD", "to": "CUST-002", "label": "Supplies Apollo Network"},
    {"from": "MKT-IN-PUN", "to": "CUST-002", "label": "Regional Backup Supply"},
    {"from": "CUST-001", "to": "ORD-2026-1001", "label": "Distribution Order"},
    {"from": "CUST-002", "to": "ORD-2026-1001", "label": "Demands 1,500 Packs"},

    # 8. Control Tower AI Risk Detection, Root Cause, and Prescriptions
    {"from": "PO-2026-001", "to": "RISK-2026-001", "label": "Direct Delay Cause"},
    {"from": "LOT-API-2026-02-QUAR", "to": "RISK-2026-001", "label": "Quarantine Shortage"},
    {"from": "ORD-2026-1001", "to": "RISK-2026-002", "label": "Hospital Fill Risk"},
    {"from": "RISK-2026-001", "to": "RISK-2026-002", "label": "Material Squeeze Cascades"},
    {"from": "RISK-2026-002", "to": "RC-2026-001", "label": "Root Cause Isolation"},
    {"from": "RISK-2026-001", "to": "RC-2026-001", "label": "Causal Root Investigation"},
    {"from": "RC-2026-001", "to": "REC-2026-001", "label": "Prescribes Air Expedite"},
    {"from": "RC-2026-001", "to": "REC-2026-002", "label": "Prescribes Buffer Transfer"},
    {"from": "RISK-2026-002", "to": "REC-2026-002", "label": "Prescribes Emergency Fill"}
]

# 3. Complete Scenario Presets with Explicit Scenario Edges
scenario_presets = {
    "scenario_a": {
        "id": "scenario_a",
        "name": "Scenario A: 14-Day Critical API Supplier Delay",
        "subtitle": "Primary Gujarat API Synthesizer Column Breakdown ➔ 150 kg Delivery Slipped +14 Days ➔ Plant Alpha Work Order Blocked ➔ Hyderabad Apollo Hospital Stockout (2,400 Packs) ➔ Autonomous Control Tower Prescribes Dedicated Air Freight (₹45,000, -7 Days)",
        "badge": "SUPPLIER DISRUPTION • HIGH RISK",
        "badgeType": "rose",
        "primaryFocusNode": "PO-2026-001",
        "nodeIds": [
            "SUP-001", "MAT-API-001", "PO-2026-001", "PROD-2026-001", 
            "SKU-AUG-500-T10", "LOC-DC-01", "MKT-IN-HYD", 
            "CUST-002", "ORD-2026-1001", "RISK-2026-001", "RISK-2026-002", 
            "RC-2026-001", "REC-2026-001"
        ],
        "scenarioEdges": [
            ["SUP-001", "MAT-API-001"],
            ["MAT-API-001", "PO-2026-001"],
            ["PO-2026-001", "PROD-2026-001"],
            ["PO-2026-001", "RISK-2026-001"],
            ["PROD-2026-001", "SKU-AUG-500-T10"],
            ["SKU-AUG-500-T10", "LOC-DC-01"],
            ["LOC-DC-01", "MKT-IN-HYD"],
            ["MKT-IN-HYD", "CUST-002"],
            ["CUST-002", "ORD-2026-1001"],
            ["ORD-2026-1001", "RISK-2026-002"],
            ["RISK-2026-001", "RISK-2026-002"],
            ["RISK-2026-001", "RC-2026-001"],
            ["RISK-2026-002", "RC-2026-001"],
            ["RC-2026-001", "REC-2026-001"]
        ],
        "flowSteps": [
            {"id": "SUP-001", "label": "1. Upstream Synthesizer (Deccan Active Pharma)"},
            {"id": "MAT-API-001", "label": "2. Raw Active Chemical (Amoxicillin / Clav API)"},
            {"id": "PO-2026-001", "label": "3. Procurement PO Slipped +14 Days (Disruption)"},
            {"id": "PROD-2026-001", "label": "4. Cleanroom Line 1 Starved (47.5 kg Deficit)"},
            {"id": "SKU-AUG-500-T10", "label": "5. Finished Commercial SKU Stock Depleted"},
            {"id": "LOC-DC-01", "label": "6. Central DC Bhiwandi Safety Stock Squeezed"},
            {"id": "MKT-IN-HYD", "label": "7. Regional Market Allocation Threatened"},
            {"id": "CUST-002", "label": "8. Apollo Hospital Network Clinical Contract"},
            {"id": "ORD-2026-1001", "label": "9. Hospital Binding Order (1,500 Packs Short)"},
            {"id": "RISK-2026-001", "label": "10. Control Tower: Material Deficit Risk (80.2)"},
            {"id": "RISK-2026-002", "label": "11. Control Tower: Commercial Stockout (84.5)"},
            {"id": "RC-2026-001", "label": "12. Causal Investigation: Column Breakdown"},
            {"id": "REC-2026-001", "label": "13. Control Tower Mitigation: Priority Air Freight"}
        ],
        "desc": "Supplier SUP-001 chromatography column failure delays 150 kg API by 14 days. Plant Alpha faces an immediate 47.5 kg deficit, halting cleanroom Work Order PROD-2026-001 and projecting a severe 2,400 pack hospital stockout in Hyderabad by Week 4. The AI Control Tower performs multi-echelon simulation and prescribes Dedicated Air Freight (₹45,000, recovering 7 days) requiring executive human sign-off."
    },
    "scenario_b": {
        "id": "scenario_b",
        "name": "Scenario B: 10-Day Finished Batch QA Release Hold",
        "subtitle": "Cleanroom Batch 10 Dissolution Failure ➔ cGMP Quarantine Hold (150 Days) ➔ Plant Alpha Line 1 Sunday Catch-Up Rerun & 3,000 Pack Buffer Reallocation",
        "badge": "CGMP QUALITY DEVIATION • QUALITY HOLD",
        "badgeType": "rose",
        "primaryFocusNode": "BATCH-AUG-2026-10",
        "nodeIds": [
            "SUP-001", "MAT-API-001", "LOT-API-2026-01", "PROD-2026-001", 
            "BATCH-AUG-2026-10", "QEV-2026-002", "LOT-API-2026-02-QUAR", 
            "RISK-2026-001", "RC-2026-001", "REC-2026-002"
        ],
        "scenarioEdges": [
            ["SUP-001", "MAT-API-001"],
            ["MAT-API-001", "LOT-API-2026-01"],
            ["LOT-API-2026-01", "PROD-2026-001"],
            ["PROD-2026-001", "BATCH-AUG-2026-10"],
            ["BATCH-AUG-2026-10", "QEV-2026-002"],
            ["QEV-2026-002", "LOT-API-2026-02-QUAR"],
            ["LOT-API-2026-02-QUAR", "RISK-2026-001"],
            ["RISK-2026-001", "RC-2026-001"],
            ["RC-2026-001", "REC-2026-002"]
        ],
        "flowSteps": [
            {"id": "SUP-001", "label": "1. Upstream Synthesizer (Deccan Active Pharma)"},
            {"id": "MAT-API-001", "label": "2. Released Raw Material Stock (Plant Alpha)"},
            {"id": "LOT-API-2026-01", "label": "3. Dispensed API Lot Feed into Cleanroom"},
            {"id": "PROD-2026-001", "label": "4. Cleanroom Compression Run PROD-2026-001"},
            {"id": "BATCH-AUG-2026-10", "label": "5. Manufactured Batch 10 (15,000 Packs In Testing)"},
            {"id": "QEV-2026-002", "label": "6. cGMP Quality Deviation: 45-Min Dissolution Failed"},
            {"id": "LOT-API-2026-02-QUAR", "label": "7. Physical Quarantine Hold: 20 kg API Locked"},
            {"id": "RISK-2026-001", "label": "8. Control Tower: Quality Release Delay Risk"},
            {"id": "RC-2026-001", "label": "9. Root Cause: Granulation Binder Ratio Deviation"},
            {"id": "REC-2026-002", "label": "10. Control Tower Mitigation: Sunday Catch-up + Transfer"}
        ],
        "desc": "Batch 10 of Augmentin T10 fails the 45-minute stage-2 dissolution threshold during QC release testing. QA Director issues QEV-2026-002, locking 20 kg of API and 15,000 packs in physical quarantine for a 150-day formal investigation. The Control Tower projects a localized stockout and autonomously schedules an emergency Sunday catch-up batch on Line 1 while reallocating 3,000 buffer packs to maintain 98.4% hospital OTIF."
    },
    "scenario_c": {
        "id": "scenario_c",
        "name": "Scenario C: Shared Packaging Component Shortage",
        "subtitle": "Western Packaging Converter Press Breakdown ➔ 40,000 Outer Carton Shortage ➔ Simultaneously Blocks Both T10 Strip & T30 Bottle Cleanrooms ➔ Secondary Converter Qualified",
        "badge": "SHARED BOM BOTTLENECK • SUPPLY HALT",
        "badgeType": "amber",
        "primaryFocusNode": "MAT-PKG-CART",
        "nodeIds": [
            "SUP-002", "MAT-PKG-CART", "PO-2026-004", "PROD-2026-001", 
            "PROD-2026-002", "SKU-AUG-500-T10", "SKU-AUG-500-T30", 
            "LOC-DC-01", "RISK-2026-001", "RC-2026-001", "REC-2026-001"
        ],
        "scenarioEdges": [
            ["SUP-002", "MAT-PKG-CART"],
            ["MAT-PKG-CART", "PO-2026-004"],
            ["PO-2026-004", "PROD-2026-001"],
            ["PO-2026-004", "PROD-2026-002"],
            ["PROD-2026-001", "SKU-AUG-500-T10"],
            ["PROD-2026-002", "SKU-AUG-500-T30"],
            ["SKU-AUG-500-T10", "LOC-DC-01"],
            ["SKU-AUG-500-T30", "LOC-DC-01"],
            ["LOC-DC-01", "RISK-2026-001"],
            ["RISK-2026-001", "RC-2026-001"],
            ["RC-2026-001", "REC-2026-001"]
        ],
        "flowSteps": [
            {"id": "SUP-002", "label": "1. Upstream Packaging Converter (Western Packaging)"},
            {"id": "MAT-PKG-CART", "label": "2. Shared Component: Printed Outer Unit Carton Box"},
            {"id": "PO-2026-004", "label": "3. PO-2026-004 (40,000 Cartons Slipped Due to Breakdown)"},
            {"id": "PROD-2026-001", "label": "4. T10 Blister Strip Cleanroom Work Order Blocked"},
            {"id": "PROD-2026-002", "label": "5. T30 HDPE Bottle Cleanroom Work Order Blocked"},
            {"id": "SKU-AUG-500-T10", "label": "6. Finished Strip Pack Commercial SKU Stalled"},
            {"id": "SKU-AUG-500-T30", "label": "7. Finished Bottle Pack Institutional SKU Stalled"},
            {"id": "LOC-DC-01", "label": "8. Bhiwandi Central DC Master Inflow Frozen"},
            {"id": "RISK-2026-001", "label": "9. Control Tower Flags Cross-SKU BOM Bottleneck"},
            {"id": "RC-2026-001", "label": "10. Root Cause: Sole-Source Secondary Converter Fault"},
            {"id": "REC-2026-001", "label": "11. Control Tower Mitigation: Emergency Secondary Converter"}
        ],
        "desc": "A mechanical breakdown at Western Packaging halts production of printed unit outer cartons (MAT-PKG-CART). Because both the 10-tablet retail blister strip (PROD-001) and the 30-tablet hospital bottle (PROD-002) share this carton in their BOM, both packaging lines are frozen simultaneously. The AI Control Tower detects the multi-line vulnerability and activates an emergency tooling run with a pre-audited secondary converter in Gujarat."
    },
    "scenario_d": {
        "id": "scenario_d",
        "name": "Scenario D: Sub-MARSL Lot Expiry Exposure",
        "subtitle": "Finished Lot 24X Approaching Expiry (< 90 Days Remaining) ➔ Tertiary Hospital Rejection Gate Breached ➔ Clearance Tender Rerouting & Fresh Lot Reallocation",
        "badge": "REGULATORY SHELF-LIFE GATE • MARSL BREACH",
        "badgeType": "amber",
        "primaryFocusNode": "LOT-FG-AUG-T10-24X",
        "nodeIds": [
            "LINE-PLANT1-01", "PROD-2026-001", "SKU-AUG-500-T10", 
            "LOT-FG-AUG-T10-24X", "LOC-DC-01", "MKT-IN-HYD", "CUST-002", 
            "ORD-2026-1001", "RISK-2026-002", "RC-2026-001", "REC-2026-002"
        ],
        "scenarioEdges": [
            ["LINE-PLANT1-01", "PROD-2026-001"],
            ["PROD-2026-001", "SKU-AUG-500-T10"],
            ["SKU-AUG-500-T10", "LOT-FG-AUG-T10-24X"],
            ["LOT-FG-AUG-T10-24X", "LOC-DC-01"],
            ["LOC-DC-01", "MKT-IN-HYD"],
            ["MKT-IN-HYD", "CUST-002"],
            ["CUST-002", "ORD-2026-1001"],
            ["ORD-2026-1001", "RISK-2026-002"],
            ["RISK-2026-002", "RC-2026-001"],
            ["RC-2026-001", "REC-2026-002"]
        ],
        "flowSteps": [
            {"id": "LINE-PLANT1-01", "label": "1. Line 1 High-Speed Granulation & Compression Facility"},
            {"id": "PROD-2026-001", "label": "2. Cleanroom Manufacturing Campaign PROD-001"},
            {"id": "SKU-AUG-500-T10", "label": "3. Commercial SKU Augmentin 500mg Strip Pack"},
            {"id": "LOT-FG-AUG-T10-24X", "label": "4. Finished Goods Lot 24X (3,000 Packs • Expiry Nov 2026)"},
            {"id": "LOC-DC-01", "label": "5. Central DC Bhiwandi Warehouse Staging Area"},
            {"id": "MKT-IN-HYD", "label": "6. Hyderabad Regional Healthcare Supply Corridor"},
            {"id": "CUST-002", "label": "7. Apollo Hospital Clinical Delivery Receiving Gate"},
            {"id": "ORD-2026-1001", "label": "8. Contract MARSL Rejection Gate (< 90 Days Breached)"},
            {"id": "RISK-2026-002", "label": "9. Control Tower Flags Contract Non-Compliance & Rejection"},
            {"id": "RC-2026-001", "label": "10. Root Cause: Standard FEFO Disregarded Hospital MARSL SLA"},
            {"id": "REC-2026-002", "label": "11. Control Tower Mitigation: Clearance Tender Reroute + Fresh Lot 26A"}
        ],
        "desc": "Central DC holds 3,000 packs of Lot 24X expiring in under 90 days. Tertiary institutional hospitals strictly enforce a 90-day Minimum Acceptable Remaining Shelf Life (MARSL) gate and will reject delivery at receiving docks. The AI Control Tower intercepts the non-compliant dispatch, reroutes Lot 24X to short-cycle retail pharmacy clearance tenders to prevent financial write-offs, and reallocates fresh commercial Lot 26A (Exp 2028) to fulfill Apollo's order."
    },
    "scenario_e": {
        "id": "scenario_e",
        "name": "Scenario E: Line Capacity Overload & Maintenance Conflict",
        "subtitle": "Overtime Catch-up Run on Line 1 Conflicts with Mandatory 4-Hour Sunday CIP Sanitation ➔ 108% Capacity Utilization Breach ➔ AI Dynamic Shift Rebalancing",
        "badge": "EQUIPMENT CAPACITY • REGULATORY CONFLICT",
        "badgeType": "purple",
        "primaryFocusNode": "LINE-PLANT1-01",
        "nodeIds": [
            "LINE-PLANT1-01", "PROD-2026-001", "PROD-2026-002", 
            "SKU-AUG-500-T10", "SKU-AUG-500-T30", "LOC-DC-01", 
            "RISK-2026-001", "RC-2026-001", "REC-2026-001"
        ],
        "scenarioEdges": [
            ["LINE-PLANT1-01", "PROD-2026-001"],
            ["LINE-PLANT1-01", "PROD-2026-002"],
            ["PROD-2026-001", "SKU-AUG-500-T10"],
            ["PROD-2026-002", "SKU-AUG-500-T30"],
            ["SKU-AUG-500-T10", "LOC-DC-01"],
            ["SKU-AUG-500-T30", "LOC-DC-01"],
            ["LOC-DC-01", "RISK-2026-001"],
            ["RISK-2026-001", "RC-2026-001"],
            ["RC-2026-001", "REC-2026-001"]
        ],
        "flowSteps": [
            {"id": "LINE-PLANT1-01", "label": "1. Line 1 Cleanroom Granulation Suite (100 hrs/wk Limit)"},
            {"id": "PROD-2026-001", "label": "2. Planned High-Speed T10 Work Order (60 Hours Scheduled)"},
            {"id": "PROD-2026-002", "label": "3. Planned T30 Bottle Compression Work Order (44 Hours Scheduled)"},
            {"id": "SKU-AUG-500-T10", "label": "4. Commercial Retail Strip Pack Commitments"},
            {"id": "SKU-AUG-500-T30", "label": "5. Institutional Hospital Bottle Commitments"},
            {"id": "LOC-DC-01", "label": "6. Central DC Master Production Schedule Replenishment"},
            {"id": "RISK-2026-001", "label": "7. Control Tower Flags 108% Line Overload & CIP Conflict"},
            {"id": "RC-2026-001", "label": "8. Root Cause: Overtime Collides with Validated 4h CIP Window"},
            {"id": "REC-2026-001", "label": "9. Control Tower Mitigation: Dynamic Shift Rescheduling"}
        ],
        "desc": "To recover lost volume, operations schedules concurrent production of T10 strips and T30 bottles on Line 1, pushing scheduled hours to 104 hours plus an overtime Sunday shift. This directly conflicts with a mandatory 4-hour cGMP Clean-in-Place (CIP) sanitization block, breaching validated capacity limits (108%). The Control Tower's finite-capacity engine reschedules T30 bottle compression to Plant 2, preserving the CIP maintenance window without compromising delivery dates."
    }
}

# 4. Replacement JS function selectGraphNode and selectScenarioPreset
replacement_functions = """        function selectGraphNode(nodeId) {
            selectedNodeId = nodeId;
            const nodeMap = {};
            GRAPH_DATA.nodes.forEach(n => { nodeMap[n.id] = n; });
            const node = nodeMap[nodeId];
            if (!node) return;

            // Check if an active scenario is currently selected
            const activeScen = (activePreset && activePreset !== 'all' && SCENARIO_PRESETS[activePreset]) 
                ? SCENARIO_PRESETS[activePreset] 
                : null;
            
            const isNodeInActiveScen = activeScen && activeScen.nodeIds.includes(nodeId);

            // Determine which edge pool to use:
            // If the user clicked a node in the active scenario, scope STRICTLY to that scenario's edges!
            let edgePool = GRAPH_DATA.edges;
            if (isNodeInActiveScen && activeScen.scenarioEdges && activeScen.scenarioEdges.length > 0) {
                const scenEdgeSet = new Set(activeScen.scenarioEdges.map(pair => pair[0] + '->' + pair[1]));
                edgePool = GRAPH_DATA.edges.filter(e => scenEdgeSet.has(e.from + '->' + e.to));
            } else if (isNodeInActiveScen) {
                const scenNodeSet = new Set(activeScen.nodeIds);
                edgePool = GRAPH_DATA.edges.filter(e => scenNodeSet.has(e.from) && scenNodeSet.has(e.to));
            }

            // Direct 1-hop Next Steps (Children)
            const directNextIds = new Set();
            const directNextEdges = [];
            edgePool.forEach(e => {
                if (e.from === nodeId) {
                    directNextIds.add(e.to);
                    directNextEdges.push(e);
                }
            });

            // Direct 1-hop Previous Steps (Parents)
            const directPrevIds = new Set();
            const directPrevEdges = [];
            edgePool.forEach(e => {
                if (e.to === nodeId) {
                    directPrevIds.add(e.from);
                    directPrevEdges.push(e);
                }
            });

            // If in full_chain mode, also compute multi-hop within the scoped edge pool
            const allUpstreamIds = new Set();
            const allDownstreamIds = new Set();
            if (graphFocusMode === 'full_chain') {
                function traceUp(currId) {
                    edgePool.forEach(e => {
                        if (e.to === currId && !allUpstreamIds.has(e.from)) {
                            allUpstreamIds.add(e.from);
                            traceUp(e.from);
                        }
                    });
                }
                traceUp(nodeId);

                function traceDown(currId) {
                    edgePool.forEach(e => {
                        if (e.from === currId && !allDownstreamIds.has(e.to)) {
                            allDownstreamIds.add(e.to);
                            traceDown(e.to);
                        }
                    });
                }
                traceDown(nodeId);
            }

            // Determine active target sets based on mode
            const activeNextSet = graphFocusMode === 'next_only' ? directNextIds : allDownstreamIds;
            const activePrevSet = graphFocusMode === 'next_only' ? directPrevIds : allUpstreamIds;

            // Update SVG Nodes
            document.querySelectorAll('.node-group').forEach(el => {
                const id = el.id.replace('node-', '');
                el.classList.remove('active', 'next-step', 'prev-step', 'upstream', 'downstream', 'dimmed', 'scenario-highlight');

                if (id === nodeId) {
                    el.classList.add('active');
                } else if (activeNextSet.has(id)) {
                    el.classList.add('next-step');
                } else if (activePrevSet.has(id)) {
                    el.classList.add('prev-step');
                } else {
                    el.classList.add('dimmed');
                }
            });

            // Update SVG Edges
            document.querySelectorAll('.edge-path').forEach(el => {
                const fromId = el.getAttribute('data-from');
                const toId = el.getAttribute('data-to');
                el.classList.remove('highlight-forward', 'highlight-backward', 'highlight-risk', 'dimmed', 'scenario-edge');

                if (fromId === nodeId && directNextIds.has(toId)) {
                    // Outgoing arrow to immediate next step in scenario
                    el.classList.add('highlight-forward');
                    el.setAttribute('marker-end', 'url(#arrow-active)');
                } else if (toId === nodeId && directPrevIds.has(fromId)) {
                    // Incoming arrow from immediate previous step in scenario
                    el.classList.add('highlight-backward');
                    el.setAttribute('marker-end', 'url(#arrow-purple)');
                } else if (graphFocusMode === 'full_chain' && allDownstreamIds.has(fromId) && allDownstreamIds.has(toId)) {
                    el.classList.add('highlight-forward');
                    el.setAttribute('marker-end', 'url(#arrow-active)');
                } else if (graphFocusMode === 'full_chain' && allUpstreamIds.has(fromId) && (allUpstreamIds.has(toId) || toId === nodeId)) {
                    el.classList.add('highlight-backward');
                    el.setAttribute('marker-end', 'url(#arrow-purple)');
                } else {
                    el.classList.add('dimmed');
                    el.setAttribute('marker-end', 'url(#arrow-default)');
                }
            });

            // Update Inspector Panel
            document.getElementById('ins-id').innerText = node.id;
            document.getElementById('ins-title').innerText = node.name;
            document.getElementById('ins-desc').innerText = node.desc || node.sub;
            document.getElementById('ins-stage-label').innerText = node.stage;
            document.getElementById('ins-db-table').innerText = node.table;

            const badge = document.getElementById('ins-status-badge');
            badge.innerText = node.status;
            badge.className = 'tag ' + (node.status === 'DELAYED' || node.status === 'HOLD' || node.status === 'QUARANTINED' || node.status === 'CRITICAL_RISK' ? 'rose' : (node.status === 'RELEASED' ? 'emerald' : 'cyan'));

            // Render Previous Steps (Parents)
            const upContainer = document.getElementById('ins-upstream-list');
            upContainer.innerHTML = '';
            if (isNodeInActiveScen) {
                const scenBadge = document.createElement('div');
                scenBadge.style.cssText = 'margin-bottom:8px; display:flex; align-items:center; justify-content:space-between; background:rgba(56,189,248,0.12); border:1px solid rgba(56,189,248,0.3); border-radius:6px; padding:5px 8px;';
                scenBadge.innerHTML = `
                    <span style="font-size:10.5px; color:#38bdf8; font-weight:600;">🎯 Filtered to ${activeScen.name.split(':')[0]}</span>
                    <button onclick="selectScenarioPreset('${activePreset}')" style="background:#1e293b; color:#cbd5e1; border:1px solid #334155; font-size:9.5px; padding:2px 6px; border-radius:4px; cursor:pointer;" title="View all nodes in this scenario">Full Chain</button>
                `;
                upContainer.appendChild(scenBadge);
            }

            if (directPrevIds.size === 0) {
                const span = document.createElement('span');
                span.style.cssText = 'color:var(--text-dim); font-size:11.5px;';
                span.innerText = isNodeInActiveScen ? 'Origin Entity (Beginning of Scenario Chain)' : 'Origin Entity (Beginning of Supply Chain)';
                upContainer.appendChild(span);
            } else {
                directPrevIds.forEach(pid => {
                    const pNode = nodeMap[pid];
                    const btn = document.createElement('button');
                    btn.className = 'prev-step-card-btn';
                    btn.onclick = () => selectGraphNode(pid);
                    btn.innerHTML = `
                        <span>⬅</span>
                        <div>
                            <strong style="color:#cbd5e1;">${pNode ? pNode.name : pid}</strong>
                            <span style="font-size:10px; color:#64748b; margin-left:4px;">(${pid})</span>
                        </div>
                    `;
                    upContainer.appendChild(btn);
                });
            }

            // Render DIRECT NEXT STEP OPTIONS (Big, Easy-to-Click Action Cards)
            const downContainer = document.getElementById('ins-downstream-list');
            downContainer.innerHTML = '';
            if (directNextIds.size === 0) {
                downContainer.innerHTML = '<span style="color:#10b981; font-size:11.5px; font-weight:600;">✓ Terminal Resolution Point (AI Recommendation Executed)</span>';
            } else {
                directNextIds.forEach(nid => {
                    const nNode = nodeMap[nid];
                    const edge = directNextEdges.find(e => e.to === nid);
                    const edgeLabel = edge && edge.label ? `&bull; ${edge.label}` : '';

                    const btn = document.createElement('button');
                    btn.className = 'next-step-card-btn';
                    btn.onclick = () => selectGraphNode(nid);
                    btn.innerHTML = `
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div class="opt-icon">${nNode ? nNode.icon : '📦'}</div>
                            <div>
                                <div class="opt-title">${nNode ? nNode.name : nid}</div>
                                <div class="opt-sub">${nid} ${edgeLabel}</div>
                            </div>
                        </div>
                        <div class="opt-arrow">➔</div>
                    `;
                    downContainer.appendChild(btn);
                });
            }
        }"""

graph_data_str = json.dumps({"nodes": nodes, "edges": edges})
presets_js_str = "const SCENARIO_PRESETS = " + json.dumps(scenario_presets, indent=12) + ";"

# Update both files
for target_file in ["db_viewer.html", "traceability_graph.html"]:
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Replace GRAPH_DATA
    g_start = content.find("const GRAPH_DATA = ")
    g_end = content.find(";", g_start)
    content = content[:g_start] + "const GRAPH_DATA = " + graph_data_str + content[g_end:]

    # 2. Replace SCENARIO_PRESETS
    s_start = content.find("const SCENARIO_PRESETS = ")
    s_end = content.find("function selectScenarioPreset", s_start)
    s_semicolon = content.rfind(";", s_start, s_end)
    content = content[:s_start] + presets_js_str + content[s_semicolon+1:]

    # 3. Replace selectGraphNode function
    fn_start = content.find("function selectGraphNode(nodeId) {")
    fn_end = content.find("const SCENARIO_PRESETS = ", fn_start)
    if fn_start != -1 and fn_end != -1:
        # find the end of selectGraphNode before SCENARIO_PRESETS
        content = content[:fn_start] + replacement_functions.strip() + "\n\n        " + content[fn_end:]

    # 4. Enhance selectScenarioPreset to highlight scenarioEdges if defined
    old_preset_edge_logic = """                if (targetNodeSet.has(fromId) && targetNodeSet.has(toId)) {
                    el.classList.add('scenario-edge');
                    el.setAttribute('marker-end', 'url(#arrow-active)');
                } else {"""
    new_preset_edge_logic = """                const isScenEdge = scen.scenarioEdges 
                    ? scen.scenarioEdges.some(pair => pair[0] === fromId && pair[1] === toId)
                    : (targetNodeSet.has(fromId) && targetNodeSet.has(toId));
                if (isScenEdge) {
                    el.classList.add('scenario-edge');
                    el.setAttribute('marker-end', 'url(#arrow-active)');
                } else {"""
    if old_preset_edge_logic in content:
        content = content.replace(old_preset_edge_logic, new_preset_edge_logic)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated " + target_file + " successfully!")

# Also sync to artifact directory
artifact_dir = r"C:\Users\prana\.gemini\antigravity\brain\5c8e60fe-0e80-4c89-963b-7356f08bbc1b"
if os.path.exists(artifact_dir):
    shutil.copy("db_viewer.html", os.path.join(artifact_dir, "db_viewer.html"))
    shutil.copy("traceability_graph.html", os.path.join(artifact_dir, "traceability_graph.html"))
    print("Synced to artifact directory successfully!")
