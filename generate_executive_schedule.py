import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def create_schedule_workbook(filepath):
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles definition
    font_family = "Segoe UI"
    
    # Colors (Corporate Navy & Slate Palette)
    NAVY_DARK = "1B365D"       # #1B365D Primary Headers
    NAVY_MID = "2F5597"        # #2F5597 Subheaders
    NAVY_LIGHT = "D9E1F2"      # #D9E1F2 Card accents
    NAVY_ACCENT = "4A90E2"     # #4A90E2 Bright accent
    ICE_BG = "F2F5F9"          # #F2F5F9 Alternate rows
    WHITE = "FFFFFF"
    GRAY_LIGHT = "E0E0E0"
    GRAY_TEXT = "595959"
    STATUS_GREEN_FILL = "E2EFDA"
    STATUS_GREEN_TEXT = "375623"
    STATUS_BLUE_FILL = "DDEBF7"
    STATUS_BLUE_TEXT = "1F4E78"
    STATUS_AMBER_FILL = "FFF2CC"
    STATUS_AMBER_TEXT = "7F6000"
    STATUS_GRAY_FILL = "F2F2F2"
    STATUS_GRAY_TEXT = "595959"

    # Borders
    thin_border = Border(
        left=Side(style='thin', color=GRAY_LIGHT),
        right=Side(style='thin', color=GRAY_LIGHT),
        top=Side(style='thin', color=GRAY_LIGHT),
        bottom=Side(style='thin', color=GRAY_LIGHT)
    )
    header_border = Border(
        left=Side(style='thin', color=WHITE),
        right=Side(style='thin', color=WHITE),
        top=Side(style='medium', color=NAVY_DARK),
        bottom=Side(style='medium', color=NAVY_DARK)
    )

    # Helper function to style ranges
    def style_header_cell(cell, text, fill_color=NAVY_DARK, text_color=WHITE, size=11, bold=True, align="center"):
        cell.value = text
        cell.font = Font(name=font_family, size=size, bold=bold, color=text_color)
        cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
        cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
        cell.border = header_border

    def style_data_cell(cell, value, size=10, bold=False, align="left", fill_color=None, text_color="000000", num_format=None):
        cell.value = value
        cell.font = Font(name=font_family, size=size, bold=bold, color=text_color)
        if fill_color:
            cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
        cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
        cell.border = thin_border
        if num_format:
            cell.number_format = num_format

    # =========================================================================
    # SHEET 1: Executive Overview & Governance
    # =========================================================================
    ws1 = wb.create_sheet(title="Executive Summary & Governance")
    ws1.views.sheetView[0].showGridLines = True

    # Title Banner
    ws1.merge_cells("A1:H1")
    title_cell = ws1["A1"]
    title_cell.value = "AI-POWERED PHARMACEUTICAL SUPPLY CHAIN CONTROL TOWER AGENT"
    title_cell.font = Font(name=font_family, size=16, bold=True, color=WHITE)
    title_cell.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    title_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[1].height = 40

    ws1.merge_cells("A2:H2")
    sub_cell = ws1["A2"]
    sub_cell.value = "12-Week Strategic Implementation Roadmap & Executive Governance Framework | Start Date: 27-Oct-2026"
    sub_cell.font = Font(name=font_family, size=11, italic=True, color=WHITE)
    sub_cell.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    sub_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[2].height = 25

    # Metadata Block
    ws1["A4"] = "PROJECT GOVERNANCE & STAKEHOLDER DIRECTORY"
    ws1["A4"].font = Font(name=font_family, size=12, bold=True, color=NAVY_DARK)
    ws1.merge_cells("A4:D4")

    gov_data = [
        ("Project Executive Sponsor:", "Director (20+ Years Pharma & Enterprise Leadership)", "Target Duration:", "12 Weeks (60 Business Days)"),
        ("Project Group Sponsor:", "Group Manager (27+ Years Global Supply Chain Operations)", "Execution Start Date:", "Tuesday, 27 October 2026"),
        ("Technical Track:", "AI Engineering / Data Science / Supply Chain Analytics", "Planned Completion Date:", "Monday, 18 January 2027"),
        ("Delivery Methodology:", "Phased Vertical Slice (1-Product Family -> Scale to 30)", "Governance Review Cadence:", "Weekly Sprint Review & Gate Sign-offs"),
        ("Data Boundary:", "Synthetic & Public Information Only (Clearly Disclaimed)", "Target Core Stack:", "Python, Pandas, Streamlit, Plotly, FastAI/Stats, LLM")
    ]

    for idx, row in enumerate(gov_data, start=5):
        ws1.row_dimensions[idx].height = 20
        style_data_cell(ws1[f"A{idx}"], row[0], size=10, bold=True, fill_color=NAVY_LIGHT)
        style_data_cell(ws1[f"B{idx}"], row[1], size=10, bold=False)
        style_data_cell(ws1[f"C{idx}"], row[2], size=10, bold=True, fill_color=NAVY_LIGHT)
        style_data_cell(ws1[f"D{idx}"], row[3], size=10, bold=False)

    # Executive Summary Cards (Metrics)
    ws1["F4"] = "CORE ARCHITECTURE DIMENSIONS"
    ws1["F4"].font = Font(name=font_family, size=12, bold=True, color=NAVY_DARK)
    ws1.merge_cells("F4:H4")

    metric_cards = [
        ("End-to-End Stages", "8 Stages", "Procurement -> QC Retest -> Plant -> Batch QA -> Distribution -> Warehousing -> Fulfilment"),
        ("Relational Schema", "33 Entities", "Master Data (8), Bridges (4), Transactions & Facts (14), Scenarios & Control Tower (7)"),
        ("Testing Benchmark", "20 Scenarios", "5 Benchmark Scenarios (A-E) + 15 Extended Operational Disruption Stress Tests"),
        ("Executive UI", "10 Pages", "Executive Overview, Forecasting, FEFO Inventory, Suppliers, QA/Plant, Logistics, Sim, AI"),
        ("AI Decision Support", "17 Questions", "Strict deterministic tool-calling with zero-hallucination citation guardrails")
    ]

    for idx, (lbl, val, desc) in enumerate(metric_cards, start=5):
        style_data_cell(ws1[f"F{idx}"], lbl, size=10, bold=True, fill_color=ICE_BG)
        style_data_cell(ws1[f"G{idx}"], val, size=10, bold=True, align="center", text_color=NAVY_DARK)
        style_data_cell(ws1[f"H{idx}"], desc, size=9, bold=False, text_color=GRAY_TEXT)

    # Executive Governance Gates Table
    ws1["A11"] = "EXECUTIVE STAGE-GATE GOVERNANCE FRAMEWORK"
    ws1["A11"].font = Font(name=font_family, size=12, bold=True, color=NAVY_DARK)
    ws1.merge_cells("A11:H11")

    gate_headers = ["Stage-Gate", "Target Horizon", "Gate Focus & Scope", "Key Technical Artifacts Required for Sign-Off", "Exit Acceptance Criteria", "Executive Sign-Off Authority", "Status"]
    ws1.row_dimensions[12].height = 26
    col_letters = ["A", "B", "C", "D", "E", "F", "G"]
    for c, h in zip(col_letters, gate_headers):
        style_header_cell(ws1[f"{c}12"], h, fill_color=NAVY_DARK, size=10)

    gates_data = [
        ("Gate 1: Foundation & Data Architecture", "Week 3 Exit (13-Nov-2026)", "Data Model, 33-Table Schema & Seeded Generator", 
         "Data Dictionary, Interactive ERD, Seeded Generator Script (seed: 20261014), Phase 1 Parquet Files",
         "100% referential integrity, zero primary key collisions, date logic verified (expiry > mfg), reproducible manifest generated.", 
         "Group Manager & Director", "Planned"),
        ("Gate 2: Deterministic Engine & Analytics", "Week 7 Exit (11-Dec-2026)", "Supply Chain Calculations, Risk Detection & Mitigation", 
         "Deterministic calculation library (FEFO, MRP, OTIF, Capacity), Risk scoring engine, Simulation sandbox",
         "Mathematical reconciliation across all stock movements; 100% precision on benchmark disruption detection; mitigation constraints checked.", 
         "Group Manager", "Planned"),
        ("Gate 3: AI Orchestration & Experience Layer", "Week 9 Exit (25-Dec-2026)", "Tool-Calling Agent & 10-Page Streamlit UI", 
         "Pydantic tool contracts, Router/Briefing agent modules, 10-page Streamlit dashboard, Plotly charts",
         "Agent answers 17 benchmark questions with zero hallucinations; all numbers cited from tool outputs; UI sub-second response.", 
         "Director & Group Manager", "Planned"),
        ("Gate 4: Final Scale-Up, Governance & Handover", "Week 12 Exit (18-Jan-2027)", "30-Product Portfolio Scale, System Card & Executive Demo", 
         "30-product synthetic dataset, 20 disruption scenarios, Responsible AI System Card, User Guide, Presentation Deck",
         "Clean-slate installation test passes; 12 official project deliverables packaged; executive showcase signed off.", 
         "Director & Senior Leadership", "Planned")
    ]

    for row_idx, r in enumerate(gates_data, start=13):
        ws1.row_dimensions[row_idx].height = 36
        bg = WHITE if row_idx % 2 != 0 else ICE_BG
        style_data_cell(ws1[f"A{row_idx}"], r[0], size=10, bold=True, fill_color=bg)
        style_data_cell(ws1[f"B{row_idx}"], r[1], size=10, bold=False, align="center", fill_color=bg)
        style_data_cell(ws1[f"C{row_idx}"], r[2], size=10, bold=False, fill_color=bg)
        style_data_cell(ws1[f"D{row_idx}"], r[3], size=9, bold=False, fill_color=bg)
        style_data_cell(ws1[f"E{row_idx}"], r[4], size=9, bold=False, fill_color=bg)
        style_data_cell(ws1[f"F{row_idx}"], r[5], size=10, bold=True, align="center", fill_color=bg, text_color=NAVY_MID)
        style_data_cell(ws1[f"G{row_idx}"], r[6], size=10, bold=True, align="center", fill_color=STATUS_BLUE_FILL, text_color=STATUS_BLUE_TEXT)

    # Core Principles & Mandates
    ws1["A18"] = "CORE ARCHITECTURAL MANDATES & GOVERNANCE PRINCIPLES"
    ws1["A18"].font = Font(name=font_family, size=12, bold=True, color=NAVY_DARK)
    ws1.merge_cells("A18:H18")

    principles = [
        ("1. Deterministic Calculation Core:", "All inventory projections, BOM explosions, capacity checks, and risk scores are executed via pure, testable Python functions. The LLM is strictly prohibited from computing numbers."),
        ("2. Zero-Hallucination Evidence Grounding:", "All narrative briefings and root-cause explanations must explicitly cite underlying record IDs (PO, Batch, Line, Lot). If evidence is absent, the agent must state uncertainty."),
        ("3. Synthetic Data Provenance:", "Every dataset, dashboard page, and generated briefing carries the mandatory disclaimer: 'Synthetic data for demonstration only. Not for operational decision making.'"),
        ("4. Human-in-the-Loop Decision Support:", "The system provides decision support, not autonomous execution. Recommendations remain pending planner review (`human_approval_required = True`)."),
        ("5. Phased Vertical Slice Execution:", "Phase 1 validates the complete 8-stage supply chain lifecycle on 1 representative product family before scaling horizontally to 30 products.")
    ]

    for p_idx, (p_title, p_desc) in enumerate(principles, start=19):
        ws1.row_dimensions[p_idx].height = 24
        style_data_cell(ws1[f"A{p_idx}"], p_title, size=10, bold=True, fill_color=NAVY_LIGHT)
        ws1.merge_cells(f"B{p_idx}:H{p_idx}")
        style_data_cell(ws1[f"B{p_idx}"], p_desc, size=10, bold=False)

    # =========================================================================
    # SHEET 2: 12-Week Master Roadmap
    # =========================================================================
    ws2 = wb.create_sheet(title="12-Week Master Roadmap")
    ws2.views.sheetView[0].showGridLines = True

    # Title Banner
    ws2.merge_cells("A1:G1")
    t2 = ws2["A1"]
    t2.value = "12-WEEK MASTER IMPLEMENTATION ROADMAP & EXIT CRITERIA"
    t2.font = Font(name=font_family, size=15, bold=True, color=WHITE)
    t2.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    t2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws2.row_dimensions[1].height = 36

    ws2.merge_cells("A2:G2")
    s2 = ws2["A2"]
    s2.value = "Weekly Strategic Focus, Key Deliverables, Formal Exit Criteria, and Governance Milestones"
    s2.font = Font(name=font_family, size=10, italic=True, color=WHITE)
    s2.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    s2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws2.row_dimensions[2].height = 22

    roadmap_headers = ["Week #", "Calendar Horizon", "Strategic Focus Area", "Project Phase / Gate", "Key Technical Deliverables", "Formal Exit Criteria", "Readiness"]
    ws2.row_dimensions[4].height = 26
    r_cols = ["A", "B", "C", "D", "E", "F", "G"]
    for c, h in zip(r_cols, roadmap_headers):
        style_header_cell(ws2[f"{c}4"], h, fill_color=NAVY_DARK, size=10)

    weeks_master = [
        ("Week 1", "27-Oct-2026 to 30-Oct-2026", "Domain Orientation, Architecture & Scope Alignment", "Phase 1: Foundation",
         "Process map (8 stages), Domain glossary, User stories, System architecture blueprint, Workspace setup",
         "Every feature mapped to a planner question; synthetic boundary confirmed; 8-stage lifecycle signed off.", "Active"),
        ("Week 2", "02-Nov-2026 to 06-Nov-2026", "Data Model & 33-Table Relational Specification", "Phase 1: Foundation",
         "33-table schema specification, Data dictionary, Interactive Mermaid ERD, Sample JSON records, Integrity constraints",
         "Each table has documented grain, primary/foreign keys, types, and referential validation rules.", "Planned"),
        ("Week 3", "09-Nov-2026 to 13-Nov-2026", "Synthetic Data Generation Engine (Phase 1 Slice)", "Phase 1: Foundation (Gate 1)",
         "Seeded Python generator (`seed: 20261014`), 104-week demand history, Phase 1 single-product dataset, Manifest, Quality report",
         "Reproducible output; referential integrity tests pass; injected benchmark scenarios trace to ground truth.", "Planned"),
        ("Week 4", "16-Nov-2026 to 20-Nov-2026", "Deterministic KPI & Inventory Projection Layer", "Phase 2: Core Engine",
         "Lot-level FEFO inventory engine, Weekly projection calculator, BOM explosion & MRP module, Capacity/OTIF metrics",
         "Inventory movements reconcile mathematically; FEFO applies strictly to eligible lots; unit tests pass.", "Planned"),
        ("Week 5", "23-Nov-2026 to 27-Nov-2026", "Demand Forecasting & Model Evaluation Layer", "Phase 2: Core Engine",
         "Baseline models (Seasonal Naive, Exp Smoothing), ML forecasting model, WAPE/Bias metrics, Forecast Model Card",
         "Unseen-period test passes; zero target leakage; forecast bounds valid; limitations documented.", "Planned"),
        ("Week 6", "30-Nov-2026 to 04-Dec-2026", "Risk Detection & Root-Cause Tracing Engine", "Phase 2: Core Engine",
         "Rule-based detector (6 risk categories), Transparent 0-100 risk score, Evidence linker (`bridge_risk_evidence`), Root-cause graph",
         "Every alert contains traceable record IDs and calculated severity; benchmark disruptions A-E detected.", "Planned"),
        ("Week 7", "07-Dec-2026 to 11-Dec-2026", "Mitigation Simulator & Feasibility Engine", "Phase 2: Core Engine (Gate 2)",
         "Simulation sandbox, Action library (Expedite PO, Reallocate DC stock, Reschedule line), Feasibility checker, Cost estimator",
         "Actions respect capacity, inventory, shelf-life, and route constraints; before/after comparison reconciled.", "Planned"),
        ("Week 8", "14-Dec-2026 to 18-Dec-2026", "Agentic AI Orchestration & Evidence Grounding", "Phase 3: AI & Experience",
         "Pydantic tool interfaces, Router agent, Evidence-grounded briefing agent, Daily morning briefing generator",
         "Numbers originate strictly from deterministic tools; agent answers 17 benchmark questions; insufficient evidence handled safely.", "Planned"),
        ("Week 9", "21-Dec-2026 to 25-Dec-2026", "Streamlit Control Tower 10-Page Application", "Phase 3: AI & Experience (Gate 3)",
         "10-page Streamlit application (Exec Overview, Forecast, Inventory, Procurement, Plant, Logistics, Risk, Sim, AI, Briefings)",
         "End-to-end user workflow validated: Detect -> Investigate -> Trace -> Simulate -> Brief; UI responsive.", "Planned"),
        ("Week 10", "28-Dec-2026 to 01-Jan-2027", "Testing, Robustness & Responsible AI Governance", "Phase 4: Scale & Handover",
         "Automated test report, Prompt injection vulnerability audit, Factuality benchmark, Responsible AI System Card",
         "Critical test suite passes; unsupported narrative claim rate measured at 0%; risk register completed.", "Planned"),
        ("Week 11", "04-Jan-2027 to 08-Jan-2027", "Portfolio Scale-Up & Stakeholder Validation", "Phase 4: Scale & Handover",
         "Expanded dataset (30 products, 10+ materials, 4 plants, 3 DCs, 8 markets, 20 scenarios), Stakeholder walkthrough",
         "Generator scales smoothly; multi-product shared material conflicts validated; stakeholder feedback ingested.", "Planned"),
        ("Week 12", "11-Jan-2027 to 18-Jan-2027", "Executive Demonstration, Handover & Archival", "Phase 4: Scale & Handover (Gate 4)",
         "Clean source repository, User Guide, Architecture Document, Executive Deck (12-15 slides), Live Showcase Demo",
         "Another engineer can execute full setup from instructions; live demo successfully delivered to Director.", "Planned")
    ]

    for idx, w in enumerate(weeks_master, start=5):
        ws2.row_dimensions[idx].height = 36
        bg = WHITE if idx % 2 != 0 else ICE_BG
        status_fill = STATUS_BLUE_FILL if w[6] == "Active" else STATUS_GRAY_FILL
        status_text = STATUS_BLUE_TEXT if w[6] == "Active" else STATUS_GRAY_TEXT
        
        style_data_cell(ws2[f"A{idx}"], w[0], size=10, bold=True, align="center", fill_color=bg)
        style_data_cell(ws2[f"B{idx}"], w[1], size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws2[f"C{idx}"], w[2], size=10, bold=True, fill_color=bg)
        style_data_cell(ws2[f"D{idx}"], w[3], size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws2[f"E{idx}"], w[4], size=9, bold=False, fill_color=bg)
        style_data_cell(ws2[f"F{idx}"], w[5], size=9, bold=False, fill_color=bg)
        style_data_cell(ws2[f"G{idx}"], w[6], size=10, bold=True, align="center", fill_color=status_fill, text_color=status_text)

    # =========================================================================
    # SHEET 3: Day-by-Day Detailed Schedule (60 Days)
    # =========================================================================
    ws3 = wb.create_sheet(title="Day-by-Day Detailed Schedule")
    ws3.views.sheetView[0].showGridLines = True

    # Title Banner
    ws3.merge_cells("A1:I1")
    t3 = ws3["A1"]
    t3.value = "COMPLETE 60-DAY OPERATIONAL WORK BREAKDOWN SCHEDULE"
    t3.font = Font(name=font_family, size=15, bold=True, color=WHITE)
    t3.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    t3.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws3.row_dimensions[1].height = 36

    ws3.merge_cells("A2:I2")
    s3 = ws3["A2"]
    s3.value = "Granular Daily Engineering Tasks, Work Products, and Governance Milestones (27-Oct-2026 to 18-Jan-2027)"
    s3.font = Font(name=font_family, size=10, italic=True, color=WHITE)
    s3.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    s3.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws3.row_dimensions[2].height = 22

    day_headers = ["Day #", "Date", "Day of Week", "Week #", "Functional Workstream", "Strategic Daily Objective", "Detailed Technical Tasks & Engineering Activities", "Deliverable / Work Product", "Milestone / Status"]
    ws3.row_dimensions[4].height = 26
    d_cols = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
    for c, h in zip(d_cols, day_headers):
        style_header_cell(ws3[f"{c}4"], h, fill_color=NAVY_DARK, size=10)

    # Generate 60 business days
    start_date = datetime.date(2026, 10, 27)
    curr_date = start_date
    calendar_days = []
    while len(calendar_days) < 60:
        if curr_date.weekday() < 5:
            calendar_days.append(curr_date)
        curr_date += datetime.timedelta(days=1)

    # Detailed daily data mapping (all 60 days)
    daily_plan = [
        # WEEK 1 (Days 1 - 4)
        (1, "Phase 1: Foundation", "Project Kick-off & Master Blueprint Ingestion", 
         "Thorough review of 15-page Intern Project Brief and master blueprint. Align on synthetic data boundaries, eliminate UK/India ambiguities, confirm Augmentin as demo product.",
         "Project charter notes, ratified scope boundaries, workspace initialized.", "Completed"),
        (2, "Phase 1: Foundation", "End-to-End Supply Chain Process Mapping", 
         "Map 8-stage pharma lifecycle: Sourcing -> QC Retest -> Manufacturing -> Batch Release -> Logistics -> Warehousing -> Fulfilment. Delineate exact handoffs and constraints.",
         "8-stage process flow diagram, cross-functional dependency matrix.", "In Progress"),
        (3, "Phase 1: Foundation", "Core Operating Principles & Terminology Formalization", 
         "Establish strict entity separation: Product Family vs Finished SKU vs Material SKU. Define Lead Time vs Cycle Time and Physical vs Eligible Inventory rules.",
         "Domain glossary document, mathematical definitions for FEFO eligibility.", "Planned"),
        (4, "Phase 1: Foundation", "Technical Architecture & Delivery Roadmap Sign-Off", 
         "Finalize 12-week schedule, directory architecture (`src/generator/`, `src/engine/`, `src/ui/`, `src/agent/`), establish tool contracts. Align with Director and Group Manager.",
         "12-Week Master Schedule Excel, ratified architectural blueprint.", "Milestone Review"),

        # WEEK 2 (Days 5 - 9)
        (5, "Data Architecture", "Master Data Entities Specification (8 Tables)", 
         "Formulate exact schemas, primary keys, and data types for `dim_product`, `dim_finished_sku`, `dim_material`, `dim_supplier`, `dim_location`, `dim_customer`, `dim_market`, `dim_production_line`.",
         "Draft master data dictionary, Pydantic schema contracts for master records.", "Planned"),
        (6, "Data Architecture", "Network Topology & Bridge Tables (4 Tables)", 
         "Define schemas for `bridge_bill_of_material` (per-unit and per-batch basis, scrap factors), `bridge_supplier_material`, `bridge_sku_market`, and `bridge_location_route`.",
         "BOM schema specification, multi-tier network connectivity matrix.", "Planned"),
        (7, "Data Architecture", "Transactional & Planning Fact Tables (9 Tables)", 
         "Specify schemas for `fact_demand_history`, `fact_customer_order`, `fact_demand_forecast`, `fact_supply_plan`, `fact_material_requirement`, `fact_inventory_projection`, `fact_purchase_order`, `fact_inventory_lot`, `fact_material_consumption`.",
         "Transactional schema specs with temporal validity and version date keys.", "Planned"),
        (8, "Data Architecture", "Manufacturing, Logistics & Risk Tables (12 Tables)", 
         "Specify schemas for `fact_production_order`, `fact_batch`, `fact_quality_event`, `fact_capacity`, `fact_shipment`, `dim_scenario`, `fact_risk_event`, `bridge_risk_evidence`, `fact_root_cause`, `fact_mitigation_simulation`, `fact_recommendation`, `dataset_manifest`.",
         "Control tower schema specification, risk-evidence relationship contract.", "Planned"),
        (9, "Data Architecture", "Entity-Relationship Diagram (ERD) Publication", 
         "Consolidate all 33 schemas into comprehensive Data Dictionary. Generate interactive visual ERD displaying primary/foreign key connections across all layers.",
         "Data Dictionary Markdown, Visual ERD diagram. Gate 1 Review Prep.", "Milestone Review"),

        # WEEK 3 (Days 10 - 14)
        (10, "Data Engineering", "Generator Architecture & Master Record Synthesizer", 
         "Implement `src/generator/master.py` with seeded random generator (`seed: 20261014`). Generate real Indian geography nodes with fictional company/supplier/plant entities.",
         "Master data generation module, reproducible seed configuration.", "Planned"),
        (11, "Data Engineering", "104-Week Historical Demand Generator", 
         "Implement `src/generator/demand.py` modeling weekly customer demand: baseline volume, trend, annual/quarterly seasonality, holiday event spikes, and controlled Gaussian noise.",
         "Historical demand dataset (104 weeks), demand variance profile report.", "Planned"),
        (12, "Data Engineering", "Supply Chain Transactions Synthesizer", 
         "Implement `src/generator/transactions.py` generating purchase orders, inventory lots with QC status/expiry, production orders, batch genealogy, and inter-city shipments.",
         "Synthetic operational transaction generator, lot-level inventory tables.", "Planned"),
        (13, "Data Engineering", "Disruption Scenario Injection Engine", 
         "Implement `src/generator/scenarios.py` injecting 5 benchmark disruptions: Supplier Delay (A), Batch QA Hold (B), Shared Material Shortage (C), Expiry Exposure (D), Mitigation Feasibility (E).",
         "Disruption injection logic, ground-truth scenario registry in `dim_scenario`.", "Planned"),
        (14, "Data Engineering", "Data Integrity Test Suite & Phase 1 Parquet Export", 
         "Write automated pytest suite verifying referential integrity, date logic (expiry > mfg, arrival > dispatch), non-negative stock balances. Export clean Parquet/SQLite dataset.",
         "Phase 1 Synthetic Dataset, `dataset_manifest.json`. Gate 1 Sign-off.", "Gate 1 Sign-Off"),

        # WEEK 4 (Days 15 - 19)
        (15, "Core Analytics", "Lot-Level Inventory Eligibility & FEFO Allocator", 
         "Develop `src/engine/inventory.py`. Implement multi-factor eligibility filter (quarantine, blocked, expired, remaining shelf life) and strictly sort eligible lots by earliest expiry date.",
         "FEFO allocation engine, lot eligibility unit test suite.", "Planned"),
        (16, "Core Analytics", "Multi-Echelon Weekly Inventory Projection Engine", 
         "Implement recursive inventory balance calculation ($I_t = I_{t-1} + R_t + P_t - D_t$). Track projected stockouts, safety stock breaches, and unmet customer demand.",
         "Weekly inventory projection engine, multi-echelon stock trajectory module.", "Planned"),
        (17, "Core Analytics", "BOM Explosion & Material Netting Engine (MRP)", 
         "Develop `src/engine/mrp.py` converting planned finished SKU production into gross component requirements. Net against eligible material stock and confirmed incoming POs.",
         "Material requirement planning engine, component shortage detector.", "Planned"),
        (18, "Core Analytics", "Supplier OTIF & Plant Line Capacity Analytics", 
         "Develop `src/engine/analytics.py` calculating supplier on-time in-full %, lead time variance, and manufacturing line capacity utilisation % (net available vs committed hours).",
         "Supplier OTIF calculator, line capacity utilisation analytics module.", "Planned"),
        (19, "Core Analytics", "Analytics Reconciliation & Mathematical Test Suite", 
         "Build reconciliation test suite proving inventory conservation across all nodes. Ensure zero unexplained stock gains or losses across historical and future horizons.",
         "Reconciliation report, automated core calculation test suite.", "Sprint Review"),

        # WEEK 5 (Days 20 - 24)
        (20, "Forecasting Layer", "Demand Time-Series Preprocessing & Splitting", 
         "Develop `src/forecasting/prep.py`. Build time-based train/validation/test splits (104 historical weeks). Enforce strict controls against future target leakage.",
         "Time-series split pipeline, data leakage audit script.", "Planned"),
        (21, "Forecasting Layer", "Baseline Statistical Forecasting Models", 
         "Implement Seasonal Naive, Moving Average, and Exponential Smoothing (Holt-Winters) models generating 26-week horizon point forecasts.",
         "Baseline forecasting module, benchmark accuracy evaluation report.", "Planned"),
        (22, "Forecasting Layer", "ML Forecasting Models & Confidence Intervals", 
         "Implement lightweight ML forecasting model (e.g. Ridge/LightGBM) with lag features, seasonal indicators, and P10/P90 prediction interval estimation.",
         "Candidate ML forecast module, probabilistic prediction interval generator.", "Planned"),
        (23, "Forecasting Layer", "Forecast Evaluation & Versioning Engine", 
         "Implement deterministic calculation of WAPE, MAE, Forecast Bias %, and Tracking Signal. Store versioned forecasts with creation timestamps in `fact_demand_forecast`.",
         "Forecast evaluation engine, versioned forecast registry.", "Planned"),
        (24, "Forecasting Layer", "Forecast Model Card & Demand Anomaly Detector", 
         "Author official Forecast Model Card detailing training horizon, error metrics, and operational limitations. Implement threshold-based demand anomaly alert.",
         "Forecast Model Card document, demand anomaly detection service.", "Sprint Review"),

        # WEEK 6 (Days 25 - 29)
        (25, "Risk & Root Cause", "Deterministic Risk Detection Engine (6 Categories)", 
         "Implement `src/engine/risk.py` detecting Stockouts, Safety Stock Breaches, Expiry Exposure, Supplier Delays, Line Capacity Overload, and Batch QA Release Delays.",
         "Rule-based risk detection service, risk event registry.", "Planned"),
        (26, "Risk & Root Cause", "Transparent Composite Risk Scoring Function", 
         "Implement transparent 0–100 risk score: $0.30S + 0.20T + 0.15C + 0.15D + 0.10U + 0.10R$. Store decomposed component scores for complete auditability.",
         "Risk scoring algorithm, scoring calibration and sensitivity test.", "Planned"),
        (27, "Risk & Root Cause", "Relational Evidence Linker (`bridge_risk_evidence`)", 
         "Implement automated evidence linking mapping each detected risk event directly to supporting database record IDs (`po_id`, `batch_id`, `lot_id`, `capacity_id`).",
         "Evidence linker module, risk-to-record traceability verification.", "Planned"),
        (28, "Risk & Root Cause", "Root-Cause Dependency Graph Engine", 
         "Implement deterministic backward causal tracing algorithm categorizing: Direct Cause, Contributing Factor, Downstream Impact, and Uncertainty.",
         "Root-cause graph engine, structured causal chain generator.", "Planned"),
        (29, "Risk & Root Cause", "Benchmark Disruption Validation Suite", 
         "Run validation tests against injected Scenarios A through E. Verify 100% detection precision, zero false negatives, and accurate causal chain attribution.",
         "Risk engine validation report, benchmark test results. Gate 2 Prep.", "Milestone Review"),

        # WEEK 7 (Days 30 - 34)
        (30, "Mitigation Engine", "Simulation Sandbox Architecture", 
         "Implement `src/engine/simulator.py`. Build isolated what-if simulation environment allowing parameter perturbations without altering baseline production records.",
         "What-if simulation sandbox, scenario state clone manager.", "Planned"),
        (31, "Mitigation Engine", "Mitigation Action 1 — Supplier Expedite Simulator", 
         "Model PO expediting: recalculate expedited arrival date, inbound QA release time, production order schedule pull-in, and downstream shortage resolution.",
         "Supplier expediting simulation service, expediting cost calculator.", "Planned"),
        (32, "Mitigation Engine", "Mitigation Action 2 — Inventory Reallocation Simulator", 
         "Model multi-echelon stock transfers: verify source DC surplus, transit lead times, freight costs, cold-chain compatibility, and arrival before impact date.",
         "Stock reallocation simulation service, inter-DC transfer validator.", "Planned"),
        (33, "Mitigation Engine", "Mitigation Action 3 — Production Rescheduling Simulator", 
         "Model manufacturing line slot adjustments: check line compatibility, component material readiness, net available capacity hours, and finished QA release.",
         "Production rescheduling simulation service, capacity conflict checker.", "Planned"),
        (34, "Mitigation Engine", "Multi-Criteria Recommendation Engine", 
         "Develop recommendation evaluator ranking options by shortage reduction %, synthetic cost, and feasibility constraints (`human_approval_required = True`).",
         "Recommendation engine, Gate 2 Technical Evaluation Report.", "Gate 2 Sign-Off"),

        # WEEK 8 (Days 35 - 39)
        (35, "Agentic AI Layer", "Analytical Tool Contracts & Pydantic Interfaces", 
         "Develop `src/agent/tools.py`. Define rigid Pydantic schemas exposing deterministic engines (`get_inventory_projection`, `get_active_risks`, `trace_root_cause`, `simulate_mitigation`).",
         "Pydantic tool contracts, tool execution wrapper with error handling.", "Planned"),
        (36, "Agentic AI Layer", "Natural Language Question Router Agent", 
         "Develop `src/agent/router.py`. Implement intent classification pipeline parsing planner queries and dispatching to approved analytical tool calls.",
         "Router agent module, query intent classifier test suite.", "Planned"),
        (37, "Agentic AI Layer", "Evidence-Grounded Briefing Agent", 
         "Develop `src/agent/briefing.py`. Build prompt templates enforcing strict factual citation of retrieved record IDs, separation of facts from assumptions, and uncertainty disclosure.",
         "Grounded briefing agent, anti-hallucination verification pipeline.", "Planned"),
        (38, "Agentic AI Layer", "17 Benchmark Planner Questions Validation", 
         "Test agent across the complete 17 benchmark questions from the project brief. Verify 100% citation precision against database records with zero fabricated claims.",
         "Agent benchmark evaluation report across 17 standard questions.", "Sprint Review"),
        (39, "Agentic AI Layer", "Automated Daily & Weekly Briefing Generator", 
         "Implement automated briefing generator converting daily calculated exceptions into structured executive summaries with risk rankings and feasible mitigations.",
         "Automated morning briefing service, weekly executive summary generator.", "Sprint Review"),

        # WEEK 9 (Days 40 - 44)
        (40, "UI & Experience", "Streamlit Multi-Page Layout & Corporate Theme", 
         "Set up Streamlit layout in `src/ui/`. Implement executive dark-navy palette, sidebar navigation, scenario selectors, and mandatory synthetic data banners.",
         "Control tower UI scaffold, responsive layout configuration.", "Planned"),
        (41, "UI & Experience", "Executive & Demand Dashboards (Pages 1 - 3)", 
         "Build Page 1: Executive Overview (KPI metric cards, priority risk queue), Page 2: Demand & Forecasting (Plotly forecast charts), Page 3: Inventory & Expiry (FEFO lot health).",
         "Pages 1-3 interactive dashboards with dynamic Plotly visualizations.", "Planned"),
        (42, "UI & Experience", "Operations & Logistics Dashboards (Pages 4 - 6)", 
         "Build Page 4: Procurement & Suppliers (open POs, OTIF gauge), Page 5: Manufacturing & Quality (line capacity heatmap, batch QA hold), Page 6: Logistics (in-transit tracking).",
         "Pages 4-6 operational dashboards with supply chain visibility.", "Planned"),
        (43, "UI & Experience", "Decision-Support & Simulation Interface (Pages 7 - 8)", 
         "Build Page 7: Risk Investigation (interactive root-cause tree, evidence inspector), Page 8: Scenario Simulation (parameter sliders, before-vs-after comparison charts).",
         "Pages 7-8 decision-support modules with what-if simulation UI.", "Planned"),
        (44, "UI & Experience", "AI Copilot & Executive Briefings Portal (Pages 9 - 10)", 
         "Build Page 9: Conversational AI Copilot (interactive chat with clickable cited records), Page 10: Executive Briefings (downloadable markdown/PDF reports).",
         "10-page fully integrated Control Tower application. Gate 3 Review.", "Gate 3 Sign-Off"),

        # WEEK 10 (Days 45 - 49)
        (45, "Testing & AI Ethics", "Comprehensive Data Quality & Stress Testing", 
         "Execute stress tests on edge cases: sudden demand spikes, zero-inventory nodes, expired lot hold, severe supplier stockouts, and conflicting production orders.",
         "Data stress test suite, robustness verification report.", "Planned"),
        (46, "Testing & AI Ethics", "Prompt Injection & Security Vulnerability Audit", 
         "Conduct adversarial security testing on AI assistant: test prompt injections, attempts to bypass tool-calling, and instructions to fabricate non-existent supply data.",
         "Security and prompt injection vulnerability audit report.", "Planned"),
        (47, "Testing & AI Ethics", "Factuality & Evidence Grounding Benchmark", 
         "Measure agent hallucination rate: verify 100% of numerical quantities and dates match calculated backend outputs. Confirm zero ungrounded causal claims.",
         "Factuality benchmark results, hallucination metric scorecard.", "Planned"),
        (48, "Testing & AI Ethics", "Responsible AI System Card Authoring", 
         "Author official Responsible AI System Card covering model boundaries, synthetic data limitations, human oversight requirements, and ethical guidelines.",
         "Responsible AI System Card, AI governance compliance document.", "Sprint Review"),
        (49, "Testing & AI Ethics", "End-to-End Regression Test Suite & Test Report", 
         "Consolidate all automated test suites (data, forecasting, deterministic engine, agent, UI). Generate comprehensive Testing & Validation Report.",
         "Consolidated Test Report, CI regression test configuration.", "Sprint Review"),

        # WEEK 11 (Days 50 - 54)
        (50, "Scale & Refinement", "Synthetic Portfolio Expansion (30 Products)", 
         "Scale generator configuration: 30 product families, shared excipients and APIs, 4 manufacturing plants, 3 regional DCs, 8 Indian markets, 6 suppliers.",
         "Scaled synthetic dataset (30 products), portfolio manifest.", "Planned"),
        (51, "Scale & Refinement", "Multi-Disruption Injection (20 Distinct Scenarios)", 
         "Populate all 20 scenario types from Section 10.3 (customs delays, cold-chain temperature excursions, yield drops, equipment outages, single-source failures).",
         "20 disruption scenarios dataset, scenario ground-truth registry.", "Planned"),
        (52, "Scale & Refinement", "System Performance Profiling & Query Optimization", 
         "Profile database queries and Streamlit caching (`@st.cache_data`). Ensure sub-second dashboard rendering and efficient memory utilisation at 30-product scale.",
         "Performance profiling report, query latency optimization patch.", "Planned"),
        (53, "Scale & Refinement", "Stakeholder Dry-Run & Interactive Walkthrough", 
         "Conduct end-to-end dry run demonstrating the core user journey: Morning Briefing -> Alert Investigation -> Root-Cause Tracing -> What-If Simulation -> Planner Approval.",
         "Stakeholder demo feedback log, prioritized backlog refinements.", "Planned"),
        (54, "Scale & Refinement", "User Feedback Ingestion & Final Polish", 
         "Implement high-priority polish items: refine UI tooltips, improve chart contrast, format executive export tables, and finalize documentation links.",
         "Polished Control Tower application ready for final executive review.", "Sprint Review"),

        # WEEK 12 (Days 55 - 60)
        (55, "Executive Handover", "Technical Documentation Finalization", 
         "Complete User Guide, Technical Architecture Blueprint, and setup instructions (`README.md`, `requirements.txt`, reproducible startup script).",
         "User Guide, Architecture Document, clean repository documentation.", "Planned"),
        (56, "Executive Handover", "Executive Presentation Deck Development", 
         "Develop 12–15 slide executive presentation deck tailored for Director and Group Manager (Executive Summary, Business Challenge, Architecture, Demo, Impact).",
         "Executive Presentation Deck (PowerPoint/PDF).", "Planned"),
        (57, "Executive Handover", "Repeatable Demo Script & Rehearsal", 
         "Script step-by-step executive demo narrative showcasing morning risk briefing, API slip scenario, multi-tier evidence tracing, and what-if mitigation comparison.",
         "Final Demonstration Script, recorded walkthrough backup.", "Planned"),
        (58, "Executive Handover", "Repository Packaging & Clean-Slate Verification", 
         "Test fresh-environment deployment from clean Git clone. Verify that automated test suite passes and dataset regenerates seamlessly from fixed seed.",
         "Packaged source repository, reproducibility verification sign-off.", "Planned"),
        (59, "Executive Handover", "Final Executive Demonstration & Showcase", 
         "Deliver formal executive presentation and live interactive Control Tower demonstration to Director (20+ yrs) and Group Manager (27+ yrs).",
         "Executive showcase delivered, formal demonstration sign-off.", "Executive Demo"),
        (60, "Executive Handover", "Formal Project Sign-Off & Internship Transition", 
         "Capture executive feedback, archive all final deliverables, document production transition roadmap, and complete formal internship project sign-off.",
         "Signed Handover Certificate, Transition Roadmap document. Project Complete.", "Gate 4 Sign-Off")
    ]

    for d_idx, (day_num, workstream, obj, tasks, output, status) in enumerate(daily_plan):
        row_num = d_idx + 5
        ws3.row_dimensions[row_num].height = 36
        c_date = calendar_days[d_idx]
        d_str = c_date.strftime("%d-%b-%Y")
        day_name = c_date.strftime("%A")
        
        # Calculate week number
        if day_num <= 4:
            wk_str = "Week 1"
        elif day_num <= 9:
            wk_str = "Week 2"
        elif day_num <= 14:
            wk_str = "Week 3"
        elif day_num <= 19:
            wk_str = "Week 4"
        elif day_num <= 24:
            wk_str = "Week 5"
        elif day_num <= 29:
            wk_str = "Week 6"
        elif day_num <= 34:
            wk_str = "Week 7"
        elif day_num <= 39:
            wk_str = "Week 8"
        elif day_num <= 44:
            wk_str = "Week 9"
        elif day_num <= 49:
            wk_str = "Week 10"
        elif day_num <= 54:
            wk_str = "Week 11"
        else:
            wk_str = "Week 12"

        bg = WHITE if day_num % 2 != 0 else ICE_BG
        
        # Status coloring
        if "Sign-Off" in status or "Executive Demo" in status:
            s_fill = STATUS_AMBER_FILL
            s_text = STATUS_AMBER_TEXT
        elif status == "Completed":
            s_fill = STATUS_GREEN_FILL
            s_text = STATUS_GREEN_TEXT
        elif status == "In Progress":
            s_fill = STATUS_BLUE_FILL
            s_text = STATUS_BLUE_TEXT
        else:
            s_fill = STATUS_GRAY_FILL
            s_text = STATUS_GRAY_TEXT

        style_data_cell(ws3[f"A{row_num}"], f"Day {day_num:02d}", size=10, bold=True, align="center", fill_color=bg)
        style_data_cell(ws3[f"B{row_num}"], d_str, size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws3[f"C{row_num}"], day_name, size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws3[f"D{row_num}"], wk_str, size=9, bold=True, align="center", fill_color=bg, text_color=NAVY_MID)
        style_data_cell(ws3[f"E{row_num}"], workstream, size=9, bold=False, fill_color=bg)
        style_data_cell(ws3[f"F{row_num}"], obj, size=10, bold=True, fill_color=bg)
        style_data_cell(ws3[f"G{row_num}"], tasks, size=9, bold=False, fill_color=bg)
        style_data_cell(ws3[f"H{row_num}"], output, size=9, bold=False, fill_color=bg)
        style_data_cell(ws3[f"I{row_num}"], status, size=9, bold=True, align="center", fill_color=s_fill, text_color=s_text)

    # =========================================================================
    # SHEET 4: Deliverables & Rubric Mapping
    # =========================================================================
    ws4 = wb.create_sheet(title="Deliverables & Rubric Matrix")
    ws4.views.sheetView[0].showGridLines = True

    # Title Banner
    ws4.merge_cells("A1:G1")
    t4 = ws4["A1"]
    t4.value = "12 OFFICIAL PROJECT DELIVERABLES & INTERNSHIP ASSESSMENT RUBRIC"
    t4.font = Font(name=font_family, size=15, bold=True, color=WHITE)
    t4.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    t4.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws4.row_dimensions[1].height = 36

    ws4.merge_cells("A2:G2")
    s4 = ws4["A2"]
    s4.value = "Mapping Deliverables to the 6 Official Internship Assessment Areas (100% Total Evaluation Weight)"
    s4.font = Font(name=font_family, size=10, italic=True, color=WHITE)
    s4.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    s4.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws4.row_dimensions[2].height = 22

    deliv_headers = ["Deliv #", "Official Deliverable Name", "Assessment Category & Weight", "Target Week", "Required Technical Content & Minimum Standards", "Acceptance Criteria", "Governance Status"]
    ws4.row_dimensions[4].height = 26
    del_cols = ["A", "B", "C", "D", "E", "F", "G"]
    for c, h in zip(del_cols, deliv_headers):
        style_header_cell(ws4[f"{c}4"], h, fill_color=NAVY_DARK, size=10)

    deliverables_data = [
        ("D-01", "Modular Source Code Repository", "Communication & Documentation (10%)", "Week 12",
         "Modular Python codebase (`src/generator/`, `src/engine/`, `src/ui/`, `src/agent/`, `tests/`), requirements.txt, setup guide, clean Git commit history.",
         "Another engineer can clone and execute end-to-end setup cleanly from instructions.", "Planned"),
        ("D-02", "Seeded Synthetic Dataset & Manifest", "Data Model & Quality (20%)", "Week 3 / 11",
         "Versioned Parquet/SQLite dataset covering 33 tables, fixed random seed (`20261014`), 104-week history, 26-week horizon, dataset manifest with row counts.",
         "Reproducible generation; zero foreign key violations; date precedence rules pass.", "Planned"),
        ("D-03", "Data Dictionary & Relational ERD", "Data Model & Quality (20%)", "Week 2",
         "Table definitions, primary/foreign keys, units of measure, data types, business definitions, and interactive visual ERD.",
         "Complete schema clarity; documented table grains; approved by technical mentors.", "Planned"),
        ("D-04", "Forecast Model Card", "Forecasting Quality (15%)", "Week 5",
         "Documentation of training periods, features, lag structures, forecast bounds, WAPE / Bias metrics, limitations, and target leakage controls.",
         "Unseen-period test passes; leakage controls verified; limitations explicitly stated.", "Planned"),
        ("D-05", "Responsible AI System Card", "Agentic AI & Grounding (15%)", "Week 10",
         "Documentation of agent boundaries, evidence-grounding mechanisms, prompt injection defenses, synthetic disclaimer, and human approval mandates.",
         "Ethical and operational guardrails ratified; zero ungrounded causal claims verified.", "Planned"),
        ("D-06", "Supply Chain Control Tower App", "Supply Chain Logic (20%)", "Week 9",
         "Interactive Streamlit application with 10 dedicated functional pages (Executive, Forecasting, FEFO Inventory, Suppliers, Plant, Logistics, Risk, Sim, AI, Briefings).",
         "End-to-end workflow (Detect -> Trace -> Simulate -> Brief) executes smoothly.", "Planned"),
        ("D-07", "Deterministic Risk & Mitigation Engine", "Risk & Recommendations (20%)", "Week 6 / 7",
         "Python engine for rule-based risk detection, transparent 0-100 risk scoring, root-cause backward tracing, and what-if simulation (Expedite, Reallocate, Reschedule).",
         "100% precision on benchmark disruption detection; feasibility constraints checked.", "Planned"),
        ("D-08", "Technical Architecture Document", "Communication & Documentation (10%)", "Week 12",
         "Comprehensive document covering system components, data flows, Pydantic tool contracts, deterministic calculation layers, and deployment assumptions.",
         "Clear component modularity; verified alignment with corporate IT standards.", "Planned"),
        ("D-09", "End-User Guide & Navigation Manual", "Communication & Documentation (10%)", "Week 12",
         "Step-by-step user manual explaining dashboard navigation, interpreting risk scores, running what-if simulations, and querying the AI copilot.",
         "Accessible to non-technical supply chain planners; clear walkthrough illustrations.", "Planned"),
        ("D-10", "Executive Presentation Deck & Demo Script", "Communication & Documentation (10%)", "Week 12",
         "12–15 slide executive PowerPoint/PDF deck, repeatable demo storyline script highlighting business value, architecture, and live simulation results.",
         "Polished, professional narrative delivered successfully to Director and Group Manager.", "Planned"),
        ("D-11", "Testing, Quality & Validation Report", "Supply Chain Logic & Quality (20%)", "Week 10",
         "Formal test report compiling data integrity results, mathematical reconciliation of stock, forecasting error analysis, risk detection recall, and AI safety audits.",
         "All critical unit and integration tests pass; mathematical reconciliation proven.", "Planned"),
        ("D-12", "Executive Morning & Weekly Briefings", "Agentic AI & Grounding (15%)", "Week 8",
         "Automated operational briefing generator summarizing active high-priority risks, root causes, feasible mitigations, synthetic costs, and pending approvals.",
         "All briefing claims cited with exact database record IDs; zero hallucinated data.", "Planned")
    ]

    for d_idx, d in enumerate(deliverables_data, start=5):
        ws4.row_dimensions[d_idx].height = 36
        bg = WHITE if d_idx % 2 != 0 else ICE_BG
        style_data_cell(ws4[f"A{d_idx}"], d[0], size=10, bold=True, align="center", fill_color=bg)
        style_data_cell(ws4[f"B{d_idx}"], d[1], size=10, bold=True, fill_color=bg)
        style_data_cell(ws4[f"C{d_idx}"], d[2], size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws4[f"D{d_idx}"], d[3], size=9, bold=True, align="center", fill_color=bg, text_color=NAVY_MID)
        style_data_cell(ws4[f"E{d_idx}"], d[4], size=9, bold=False, fill_color=bg)
        style_data_cell(ws4[f"F{d_idx}"], d[5], size=9, bold=False, fill_color=bg)
        style_data_cell(ws4[f"G{d_idx}"], d[6], size=9, bold=True, align="center", fill_color=STATUS_BLUE_FILL, text_color=STATUS_BLUE_TEXT)

    # Assessment Rubric Summary Table
    ws4["A19"] = "OFFICIAL INTERNSHIP ASSESSMENT EVALUATION WEIGHTS"
    ws4["A19"].font = Font(name=font_family, size=12, bold=True, color=NAVY_DARK)
    ws4.merge_cells("A19:G19")

    rubric_headers = ["Assessment Area", "Evaluation Weight", "Evaluation Evidence & Acceptance Standards"]
    ws4.row_dimensions[20].height = 24
    style_header_cell(ws4["A20"], rubric_headers[0], fill_color=NAVY_MID, size=10)
    style_header_cell(ws4["B20"], rubric_headers[1], fill_color=NAVY_MID, size=10)
    ws4.merge_cells("C20:G20")
    style_header_cell(ws4["C20"], rubric_headers[2], fill_color=NAVY_MID, size=10)

    rubrics = [
        ("Data Model & Quality", "20%", "33-table schema design, referential integrity, range tests, date logic, and seeded reproducibility."),
        ("Supply Chain Logic", "20%", "Mathematical correctness of stock projections, FEFO eligibility, BOM explosion, and capacity utilisation."),
        ("Forecasting Quality", "15%", "Baseline comparisons, WAPE/Bias metrics, test design without target leakage, and documented limitations."),
        ("Risk & Recommendations", "20%", "Traceability of alerts to records, transparent 0-100 risk scoring, feasibility constraints, and scenario impact."),
        ("Agentic AI & Grounding", "15%", "Tool interface contracts, evidence citation, zero-hallucination rate, and safe handling of unknowns."),
        ("Communication & Documentation", "10%", "Clarity of technical documentation, ERD, code readability, User Guide, and executive demo delivery.")
    ]

    for r_idx, (r_area, r_wt, r_evid) in enumerate(rubrics, start=21):
        ws4.row_dimensions[r_idx].height = 22
        bg = WHITE if r_idx % 2 != 0 else ICE_BG
        style_data_cell(ws4[f"A{r_idx}"], r_area, size=10, bold=True, fill_color=bg)
        style_data_cell(ws4[f"B{r_idx}"], r_wt, size=10, bold=True, align="center", fill_color=NAVY_LIGHT, text_color=NAVY_DARK)
        ws4.merge_cells(f"C{r_idx}:G{r_idx}")
        style_data_cell(ws4[f"C{r_idx}"], r_evid, size=9, bold=False, fill_color=bg)

    # =========================================================================
    # SHEET 5: Disruption Scenarios & Risk Test
    # =========================================================================
    ws5 = wb.create_sheet(title="Disruption Scenarios & Testing")
    ws5.views.sheetView[0].showGridLines = True

    # Title Banner
    ws5.merge_cells("A1:G1")
    t5 = ws5["A1"]
    t5.value = "BENCHMARK OPERATIONAL DISRUPTION SCENARIOS & TESTING MATRIX"
    t5.font = Font(name=font_family, size=15, bold=True, color=WHITE)
    t5.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    t5.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws5.row_dimensions[1].height = 36

    ws5.merge_cells("A2:G2")
    s5 = ws5["A2"]
    s5.value = "Catalog of Injected Supply Chain Shocks, Affected Stages, Ground-Truth Causal Chains, and Expected System Responses"
    s5.font = Font(name=font_family, size=10, italic=True, color=WHITE)
    s5.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    s5.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws5.row_dimensions[2].height = 22

    scen_headers = ["Scenario ID", "Disruption Scenario Name", "Supply Chain Stage", "Technical Injection Mechanism", "Ground-Truth Causal Chain", "Expected Control Tower Alert", "Candidate Mitigation Options"]
    ws5.row_dimensions[4].height = 26
    sc_cols = ["A", "B", "C", "D", "E", "F", "G"]
    for c, h in zip(sc_cols, scen_headers):
        style_header_cell(ws5[f"{c}4"], h, fill_color=NAVY_DARK, size=10)

    scenarios_data = [
        ("SCN-A", "API Delivery Delay", "Procurement & Sourcing", 
         "Shift actual receipt date on critical API purchase order 14 days beyond promised delivery date.",
         "Delayed PO arrival -> Raw material stockout -> Postponed production start -> Finished batch release delayed -> DC stockout in Week 4.",
         "High-Severity Stockout Alert linking to delayed PO and upstream supplier SUP-001.",
         "Simulate Supplier Expedite vs Inventory Reallocation from alternate DC."),
        ("SCN-B", "Batch QA Release Delay", "Quality & Release", 
         "Finished goods batch completed on time, but QA release date shifted +10 days due to pending sterility testing.",
         "Batch physical stock present at plant but unreleased -> Ineligible for distribution -> DC replenishment delayed -> Market safety stock breach.",
         "Batch-Release Delay Alert; inventory projection accurately excludes unreleased stock.",
         "Simulate Expedited QA Testing vs Fast-Track Logistics dispatch."),
        ("SCN-C", "Shared Packaging Shortage", "Component Planning", 
         "Synthetic carton shortage (`MAT-PKG-CART`) delays packaging line across multiple finished SKUs (T10 and T30).",
         "Bulk tablets available but carton stock insufficient -> Multiple finished SKUs blocked from packaging -> Multi-market shortage.",
         "Cross-SKU Material Shortage Alert highlighting shared component bottleneck.",
         "Simulate Alternative Packaging Supplier vs Production Prioritization to critical SKU."),
        ("SCN-D", "FEFO Expiry Exposure", "Warehousing & Inventory", 
         "Batch of finished product has 45 days remaining shelf life, below destination market minimum acceptance threshold (90 days).",
         "Stock physically on-hand at DC -> Filtered out by eligibility rule -> Projected inventory drops -> Imminent stockout.",
         "Expiry Exposure & Inventory Ineligibility Alert; FEFO allocator safely bypasses lot.",
         "Simulate Reallocation to institutional hospital market with shorter shelf-life rule."),
        ("SCN-E", "Mitigation Feasibility Conflict", "Decision Support / Sim", 
         "Supplier expediting successfully accelerates API delivery, but manufacturing line ALPHA-01 has scheduled maintenance that same week.",
         "Expedited material arrives on time -> Plant line unavailable due to committed hours -> Production remains delayed.",
         "Infeasible Mitigation Warning: System alerts planner that expediting material alone does not resolve finished stockout.",
         "Simulate Combined Action: Expedite Material + Reschedule Production to Line BETA-02.")
    ]

    for s_idx, sc in enumerate(scenarios_data, start=5):
        ws5.row_dimensions[s_idx].height = 36
        bg = WHITE if s_idx % 2 != 0 else ICE_BG
        style_data_cell(ws5[f"A{s_idx}"], sc[0], size=10, bold=True, align="center", fill_color=bg)
        style_data_cell(ws5[f"B{s_idx}"], sc[1], size=10, bold=True, fill_color=bg)
        style_data_cell(ws5[f"C{s_idx}"], sc[2], size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws5[f"D{s_idx}"], sc[3], size=9, bold=False, fill_color=bg)
        style_data_cell(ws5[f"E{s_idx}"], sc[4], size=9, bold=False, fill_color=bg)
        style_data_cell(ws5[f"F{s_idx}"], sc[5], size=9, bold=False, fill_color=bg)
        style_data_cell(ws5[f"G{s_idx}"], sc[6], size=9, bold=False, fill_color=bg)

    # Auto-adjust column widths for all sheets
    for ws in [ws1, ws2, ws3, ws4, ws5]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                # ignore merged cells in length calculation
                if cell.coordinate in ws.merged_cells:
                    continue
                if cell.value:
                    lines = str(cell.value).split("\n")
                    for line in lines:
                        if len(str(line)) > max_len:
                            max_len = len(str(line))
            # Column specific rules
            if col_letter in ["A"]:
                ws.column_dimensions[col_letter].width = max(max_len + 3, 14)
            elif col_letter in ["B", "C", "D"]:
                ws.column_dimensions[col_letter].width = max(max_len + 3, 18)
            else:
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 22), 65)

    # Custom width overrides for specific sheets
    ws1.column_dimensions["A"].width = 24
    ws1.column_dimensions["B"].width = 38
    ws1.column_dimensions["C"].width = 24
    ws1.column_dimensions["D"].width = 38
    ws1.column_dimensions["E"].width = 6
    ws1.column_dimensions["F"].width = 22
    ws1.column_dimensions["G"].width = 16
    ws1.column_dimensions["H"].width = 45

    ws2.column_dimensions["A"].width = 12
    ws2.column_dimensions["B"].width = 28
    ws2.column_dimensions["C"].width = 35
    ws2.column_dimensions["D"].width = 22
    ws2.column_dimensions["E"].width = 45
    ws2.column_dimensions["F"].width = 48
    ws2.column_dimensions["G"].width = 14

    ws3.column_dimensions["A"].width = 10
    ws3.column_dimensions["B"].width = 14
    ws3.column_dimensions["C"].width = 14
    ws3.column_dimensions["D"].width = 12
    ws3.column_dimensions["E"].width = 20
    ws3.column_dimensions["F"].width = 35
    ws3.column_dimensions["G"].width = 52
    ws3.column_dimensions["H"].width = 38
    ws3.column_dimensions["I"].width = 16

    ws4.column_dimensions["A"].width = 12
    ws4.column_dimensions["B"].width = 32
    ws4.column_dimensions["C"].width = 28
    ws4.column_dimensions["D"].width = 16
    ws4.column_dimensions["E"].width = 45
    ws4.column_dimensions["F"].width = 45
    ws4.column_dimensions["G"].width = 16

    ws5.column_dimensions["A"].width = 14
    ws5.column_dimensions["B"].width = 28
    ws5.column_dimensions["C"].width = 22
    ws5.column_dimensions["D"].width = 42
    ws5.column_dimensions["E"].width = 48
    ws5.column_dimensions["F"].width = 40
    ws5.column_dimensions["G"].width = 40

    # Freeze panes on data tables for executive review
    ws2.freeze_panes = 'A5'
    ws3.freeze_panes = 'A5'
    ws4.freeze_panes = 'A5'
    ws5.freeze_panes = 'A5'

    wb.save(filepath)
    print(f"Workbook successfully generated and saved at: {filepath}")

if __name__ == "__main__":
    out_path = r"d:\AI Pharmaceutical Supply Chain\AI_Supply_Chain_Control_Tower_12_Week_Executive_Schedule.xlsx"
    create_schedule_workbook(out_path)
