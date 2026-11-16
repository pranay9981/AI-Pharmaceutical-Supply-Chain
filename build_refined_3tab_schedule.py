import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def generate_3tab_executive_schedule(filepath):
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    font_family = "Segoe UI"
    
    NAVY_DARK = "1B365D"       # #1B365D - Dominant Executive Navy
    NAVY_MID = "2C4D75"        # #2C4D75 - Supporting Slate Blue
    NAVY_LIGHT = "E8EEF5"      # #E8EEF5 - Subtle Data Row Tint
    GOLD_ACCENT = "C59B27"     # #C59B27 - Gate / Milestone Gold
    WHITE = "FFFFFF"
    BORDER_GRAY = "D1D5DB"
    ICE_BG = "F8FAFC"
    
    STATUS_GREEN_FILL = "DEF7EC"
    STATUS_GREEN_TEXT = "03543F"
    STATUS_BLUE_FILL = "E1EFFE"
    STATUS_BLUE_TEXT = "1E429F"
    STATUS_AMBER_FILL = "FEF08A"
    STATUS_AMBER_TEXT = "713F12"
    STATUS_PURPLE_FILL = "F3E8FF"
    STATUS_PURPLE_TEXT = "6B21A8"
    STATUS_GRAY_FILL = "F3F4F6"
    STATUS_GRAY_TEXT = "374151"

    thin_border = Border(
        left=Side(style='thin', color=BORDER_GRAY),
        right=Side(style='thin', color=BORDER_GRAY),
        top=Side(style='thin', color=BORDER_GRAY),
        bottom=Side(style='thin', color=BORDER_GRAY)
    )

    def style_header_cell(cell, text, fill_color=NAVY_DARK, text_color=WHITE, size=11, bold=True, align="center"):
        cell.value = text
        cell.font = Font(name=font_family, size=size, bold=bold, color=text_color)
        cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
        cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
        cell.border = thin_border

    def style_data_cell(cell, value, size=10, bold=False, align="left", fill_color=WHITE, text_color="000000"):
        cell.value = value
        cell.font = Font(name=font_family, size=size, bold=bold, color=text_color)
        if fill_color != WHITE:
            cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
        cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
        cell.border = thin_border

    # =========================================================================
    # TAB 1: 4-PHASE STRATEGIC EXECUTION BREAKDOWN & GATE OUTCOMES
    # =========================================================================
    ws1 = wb.create_sheet(title="Phase Strategic Breakdown")
    ws1.views.sheetView[0].showGridLines = True

    # Title Banner
    ws1.merge_cells("A1:G1")
    t1 = ws1["A1"]
    t1.value = "AI PHARMACEUTICAL SUPPLY CHAIN CONTROL TOWER — 4-PHASE STRATEGIC BREAKDOWN"
    t1.font = Font(name=font_family, size=15, bold=True, color=WHITE)
    t1.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    t1.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[1].height = 36

    ws1.merge_cells("A2:G2")
    st1 = ws1["A2"]
    st1.value = "Strategic Focus, Daily Implementation Roadmap, Concrete Deliverables, Defensible Exit Standards & Governance Sign-Off"
    st1.font = Font(name=font_family, size=10, italic=True, color=WHITE)
    st1.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    st1.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[2].height = 22

    # Executive Governance Footnote / Scope Clarification Bar
    ws1.merge_cells("A3:G3")
    fn1 = ws1["A3"]
    fn1.value = "Scope Rule: Architecture specifies 33 relational tables; 30 tables populated with 691 baseline records (3 dynamic engine tables populated during Phase 2 execution). Geographic network defaults to India with region-agnostic parameters."
    fn1.font = Font(name=font_family, size=8.5, italic=True, color=NAVY_DARK)
    fn1.fill = PatternFill(start_color=NAVY_LIGHT, end_color=NAVY_LIGHT, fill_type="solid")
    fn1.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[3].height = 20

    phase_headers = ["Phase Name & Identifier", "Timeline & Working Days", "Strategic Intent & Scope", "Daily Implementation Roadmap", "Tangible Final Deliverables & Work Products", "Defensible Exit Quality Standards", "Gate Review Authority"]
    p_cols = ["A", "B", "C", "D", "E", "F", "G"]
    ws1.row_dimensions[5].height = 28
    for c, h in zip(p_cols, phase_headers):
        style_header_cell(ws1[f"{c}5"], h, fill_color=NAVY_DARK, size=10)

    phases_data = [
        (
            "PHASE 1:\nFoundation & Data Architecture",
            "Weeks 1 to 3\n(Days 01 - 14)\n27-Oct to 13-Nov-2026",
            "Establish domain contracts, 33-table relational schema (30 baseline + 3 dynamic), seeded generator, and the complete 8-stage single-product vertical slice (Augmentin T10 strip & T30 bottle packs) across a parameterized Indian supply chain network.",
            "• Days 1-4: Project charter, 8-stage lifecycle mapping, entity hierarchy (Product Family vs SKU vs Material), architectural sign-off.\n• Days 5-9: 33-table schema design (8 Master, 4 Bridges, 9 Facts, 5 Mfg/Logistics, 6 Risk/Simulation, 1 Audit), Data Dictionary & ERD.\n• Days 10-14: Implement generator modules (`config.py`, `master_data.py`, `demand_data.py`, `supply_data.py`, `disruption_injector.py`, `runner.py`), inject Scenario A (14-day API delay), execute pytest integrity suite.",
            "1. 33-Table Relational Schema & Data Dictionary (docs/data_dictionary.md).\n2. Interactive Mermaid ERD (docs/erd_diagram.md).\n3. Seeded Synthetic Generator (seed: 20261014; 104 historical + 26 forecast weeks).\n4. Phase 1 Production Dataset: 691 verified records across 30 tables in CSV, Parquet, and SQLite (control_tower.db).\n5. 30-Tab Database Excel Viewer & Interactive HTML Database Explorer.\n6. Automated Pytest Data Integrity Suite (7 passing tests).",
            "• 100% referential integrity across all foreign keys; zero primary key collisions.\n• Strict date logic validation (Expiry > Mfg Date; Arrival >= Dispatch Date).\n• Zero negative inventory balances; 100% reproducible generation from fixed seed.",
            "Gate 1 Sign-Off:\nGroup Manager & Director"
        ),
        (
            "PHASE 2:\nDeterministic Analytics & Core Engines",
            "Weeks 4 to 7\n(Days 15 - 34)\n16-Nov to 11-Dec-2026",
            "Build pure Python, testable analytical and simulation engines (inventory projection, BOM explosion, demand forecasting with P10/P90 prediction intervals, risk scoring, and what-if simulation) with strictly zero LLM mathematical calculations.",
            "• Days 15-19: Lot-level FEFO eligibility and multi-echelon stock projection ($I_t = I_{t-1} + R_t + P_t - D_t$); MRP component netting; OTIF & capacity analytics; Day 19 mathematical reconciliation buffer.\n• Days 20-24: Time-series split (leakage controls), baseline models (Seasonal Naive, Exp Smoothing), ML forecasting (lag features, P10/P90 intervals), WAPE/Bias metrics, Forecast Model Card.\n• Days 25-29: Rule-based risk detector (6 categories), composite risk score ($0.30S+0.20T+0.15C+0.15D+0.10U+0.10R$), evidence linker (`bridge_risk_evidence`), backward causal tracing graph, Scenarios A-E benchmark validation.\n• Days 30-34: Non-destructive simulation sandbox (`src/engine/simulator.py`), 3 actions (Supplier Expedite, Stock Transfer, Production Reschedule), multi-criteria recommendation engine; Day 34 Gate 2 review & integration buffer.",
            "1. Pure Python Analytical Engine Suite (`src/engine/inventory.py`, `mrp.py`, `analytics.py`).\n2. Forecast Model Card with WAPE, MAE, Bias %, and P10/P90 interval benchmarks.\n3. Risk Detection & Root-Cause Tracing Service (`src/engine/risk.py`).\n4. What-If Simulation Sandbox (`src/engine/simulator.py`) with feasibility & cost checks (`human_approval_required = True`).\n5. Stock Reconciliation Report proving mathematical conservation of inventory.",
            "• Mathematical conservation: 0.0% unexplained inventory drift across all echelons.\n• Benchmark disruption detection: 100% recall and >=95% precision on Scenarios A-E against injection manifests.\n• Simulation feasibility: 100% of tested mitigations pass shelf-life, transit lead time, and machine capacity constraints.",
            "Gate 2 Sign-Off:\nGroup Manager"
        ),
        (
            "PHASE 3:\nAgentic AI Orchestration & Experience Layer",
            "Weeks 8 to 9\n(Days 35 - 44)\n14-Dec to 25-Dec-2026",
            "Build the evidence-grounded AI copilot using rigid Pydantic tool contracts and the 10-page Streamlit Control Tower application providing visual executive visibility and conversational decision-support.",
            "• Days 35-39: Define Pydantic tool interfaces (`src/agent/tools.py`), intent router agent, grounded briefing agent with citation enforcement, validate against 17 benchmark planner questions, automated executive morning briefing generator.\n• Days 40-44: Build 10-page Streamlit app (`src/ui/`): Pages 1-3 (Executive, Demand, Inventory), Pages 4-6 (Suppliers, Plant, Logistics), Pages 7-8 (Risk Investigation, Simulation), Pages 9-10 (AI Copilot, Briefings); Day 43 Gate 3 pre-holiday integration & sign-off; Day 44 Corporate Holiday (Christmas buffer).",
            "1. Grounded AI Agent Framework answering 17 benchmark planner questions with zero hallucinations.\n2. Automated Morning & Weekly Executive Briefing generator citing exact record IDs.\n3. Full 10-Page Interactive Streamlit Control Tower Application with Plotly visualizations.\n4. End-to-end user workflow: Detect Alert -> Investigate Root Cause -> Simulate Mitigations -> Briefing -> Approval.",
            "• Evidence Grounding: 100% of numerical quantities and dates in agent briefings cite verified record IDs (`po_id`, `batch_id`, `lot_id`); 0 ungrounded claims.\n• UI Responsiveness: <=1.0s for cached metric views and page transitions; <=3.0s for multi-echelon simulation recalculations.\n• Workflow Validation: Successful execution of all 17 benchmark planner questions.",
            "Gate 3 Sign-Off:\nDirector & Group Manager"
        ),
        (
            "PHASE 4:\nScale-Up, Responsible AI & Final Handover",
            "Weeks 10 to 12\n(Days 45 - 60)\n28-Dec-2026 to 18-Jan-2027",
            "Contingent horizontal scale-up to 30 products and 20 disruption scenarios, comprehensive AI ethics and adversarial security testing, documentation, and executive showcase delivery.",
            "• Days 45-49: Data edge-case stress testing, prompt injection & security audit, factuality benchmark, Responsible AI System Card, consolidated regression suite; Day 49 Corporate Holiday (New Year's Day buffer).\n• Days 50-54: Stretch Portfolio Scale-Up: Expand generator to 30 products, 10+ materials, 4 plants, 3 DCs, 8 markets, 6 suppliers, 20 disruption scenarios; query profiling; stakeholder interactive dry-run; UI feedback polish.\n• Days 55-60: Finalize User Guide & Architecture Blueprint; develop 12-15 slide Executive Deck; scripted demo rehearsal; clean-slate Git repository packaging; live executive showcase demonstration; internship sign-off.",
            "1. Scaled 30-Product Synthetic Dataset with 20 Disruption Scenarios.\n2. Responsible AI System Card & Security/Prompt-Injection Audit Report.\n3. Complete User Guide & Technical Architecture Blueprint.\n4. Executive Presentation Deck (12-15 slides) & Scripted Demo Storyline.\n5. Production-Packaged Git Repository with clean setup instructions.\n6. Formal Executive Demonstration delivered to Director (20+ yrs) and Group Manager (27+ yrs).",
            "• Clean-slate installation: 100% automated build and test pass on a fresh machine environment.\n• AI Safety: 0 prompt injection bypasses; 0 unsupported claims on factuality benchmark.\n• Scale Stability: <=1.5s average dashboard query latency at 30-product portfolio volume.\n• Executive Acceptance: Live showcase demonstration formally approved.",
            "Gate 4 Sign-Off:\nDirector & Senior Leadership"
        )
    ]

    for p_idx, p in enumerate(phases_data, start=6):
        ws1.row_dimensions[p_idx].height = 115
        bg = WHITE if p_idx % 2 != 0 else ICE_BG
        style_data_cell(ws1[f"A{p_idx}"], p[0], size=10, bold=True, align="center", fill_color=NAVY_LIGHT, text_color=NAVY_DARK)
        style_data_cell(ws1[f"B{p_idx}"], p[1], size=9, bold=True, align="center", fill_color=bg)
        style_data_cell(ws1[f"C{p_idx}"], p[2], size=9, bold=False, fill_color=bg)
        style_data_cell(ws1[f"D{p_idx}"], p[3], size=9, bold=False, fill_color=bg)
        style_data_cell(ws1[f"E{p_idx}"], p[4], size=9, bold=False, fill_color=bg)
        style_data_cell(ws1[f"F{p_idx}"], p[5], size=8.5, bold=False, fill_color=bg)
        style_data_cell(ws1[f"G{p_idx}"], p[6], size=9, bold=True, align="center", fill_color=STATUS_AMBER_FILL, text_color=STATUS_AMBER_TEXT)

    # =========================================================================
    # TAB 2: 12-WEEK MASTER IMPLEMENTATION ROADMAP & EXIT CRITERIA
    # =========================================================================
    ws2 = wb.create_sheet(title="12-Week Master Roadmap")
    ws2.views.sheetView[0].showGridLines = True

    # Title Banner
    ws2.merge_cells("A1:G1")
    t2 = ws2["A1"]
    t2.value = "12-WEEK MASTER IMPLEMENTATION ROADMAP & GOVERNANCE GATES"
    t2.font = Font(name=font_family, size=15, bold=True, color=WHITE)
    t2.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    t2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws2.row_dimensions[1].height = 36

    ws2.merge_cells("A2:G2")
    st2 = ws2["A2"]
    st2.value = "Weekly Strategic Focus, Key Work Products, Defensible Exit Standards, and Governance Milestones (27-Oct-2026 to 18-Jan-2027)"
    st2.font = Font(name=font_family, size=10, italic=True, color=WHITE)
    st2.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    st2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws2.row_dimensions[2].height = 22

    # Executive Governance Footnote / Scope Clarification Bar
    ws2.merge_cells("A3:G3")
    fn2 = ws2["A3"]
    fn2.value = "Schedule Structure: 12 Calendar Weeks | 58 Active Engineering Days + 2 Scheduled Corporate Holidays / Buffers (25-Dec Christmas & 01-Jan New Year's Day) = 60 Weekdays."
    fn2.font = Font(name=font_family, size=8.5, italic=True, color=NAVY_DARK)
    fn2.fill = PatternFill(start_color=NAVY_LIGHT, end_color=NAVY_LIGHT, fill_type="solid")
    fn2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws2.row_dimensions[3].height = 20

    roadmap_headers = ["Week #", "Calendar Horizon", "Strategic Focus Area", "Project Phase / Gate", "Key Technical Deliverables", "Defensible Exit Criteria", "Readiness / Status"]
    ws2.row_dimensions[5].height = 26
    r_cols = ["A", "B", "C", "D", "E", "F", "G"]
    for c, h in zip(r_cols, roadmap_headers):
        style_header_cell(ws2[f"{c}5"], h, fill_color=NAVY_DARK, size=10)

    weeks_master = [
        ("Week 1", "27-Oct-2026 to 30-Oct-2026", "Domain Orientation, Architecture & Scope Alignment", "Phase 1: Foundation",
         "Process map (8 stages), Domain glossary, User stories, System architecture blueprint, Workspace setup",
         "Every feature mapped to a planner question; synthetic boundary confirmed; 8-stage lifecycle signed off.", "Completed"),
        ("Week 2", "02-Nov-2026 to 06-Nov-2026", "Data Model & 33-Table Relational Specification", "Phase 1: Foundation",
         "33-table schema specification (30 baseline + 3 dynamic), Data dictionary, Interactive Mermaid ERD, Pydantic contracts",
         "Each table has documented grain, primary/foreign keys, types, and referential validation rules.", "Completed"),
        ("Week 3", "09-Nov-2026 to 13-Nov-2026", "Synthetic Data Generation Engine (Phase 1 Slice)", "Phase 1: Foundation (Gate 1)",
         "Seeded Python generator (`seed: 20261014`), 104-week demand history, Phase 1 dataset (691 rows across 30 tables), Manifest, Pytest suite",
         "100% referential integrity; date logic verified; zero PK collisions; reproducible output confirmed.", "Completed"),
        ("Week 4", "16-Nov-2026 to 20-Nov-2026", "Deterministic KPI & Inventory Projection Layer", "Phase 2: Core Engine",
         "Lot-level FEFO inventory engine, Weekly projection calculator ($I_t = I_{t-1} + R_t + P_t - D_t$), BOM explosion & MRP module, Capacity/OTIF metrics",
         "Mathematical conservation: 0.0% unexplained inventory drift across all echelons; unit tests pass.", "Completed"),
        ("Week 5", "23-Nov-2026 to 27-Nov-2026", "Demand Forecasting & Model Evaluation Layer", "Phase 2: Core Engine",
         "Baseline models (Seasonal Naive, Exp Smoothing), ML forecasting model with P10/P90 intervals, WAPE/Bias metrics, Forecast Model Card",
         "Unseen-period test passes; zero target leakage; forecast bounds valid; limitations documented.", "Active"),
        ("Week 6", "30-Nov-2026 to 04-Dec-2026", "Risk Detection & Root-Cause Tracing Engine", "Phase 2: Core Engine",
         "Rule-based detector (6 risk categories), Transparent 0-100 risk score, Evidence linker (`bridge_risk_evidence`), Root-cause graph",
         "Every alert contains traceable record IDs and calculated severity; benchmark disruptions A-E detected.", "Planned"),
        ("Week 7", "07-Dec-2026 to 11-Dec-2026", "Mitigation Simulator & Feasibility Engine", "Phase 2: Core Engine (Gate 2)",
         "Simulation sandbox, Action library (Expedite PO, Reallocate DC stock, Reschedule line), Feasibility checker, Cost estimator",
         "100% precision on benchmark disruption detection; mitigation constraints checked; before/after reconciled.", "Planned"),
        ("Week 8", "14-Dec-2026 to 18-Dec-2026", "Agentic AI Orchestration & Evidence Grounding", "Phase 3: AI & Experience",
         "Pydantic tool interfaces, Router agent, Evidence-grounded briefing agent, Daily morning briefing generator",
         "Numbers originate strictly from deterministic tools; agent answers 17 benchmark questions; insufficient evidence handled safely.", "Planned"),
        ("Week 9", "21-Dec-2026 to 25-Dec-2026", "Streamlit Control Tower & Gate 3 Review", "Phase 3: AI & Experience (Gate 3)",
         "10-page Streamlit app; pre-holiday Gate 3 Review on 24-Dec; Corporate Holiday & stability buffer on 25-Dec (Christmas)",
         "End-to-end workflow validated (Detect -> Trace -> Simulate -> Brief); UI sub-second response on cached queries.", "Planned"),
        ("Week 10", "28-Dec-2026 to 01-Jan-2027", "Testing, Robustness & Responsible AI Governance", "Phase 4: Scale & Handover",
         "Automated test report, Prompt injection vulnerability audit, Factuality benchmark, Responsible AI System Card; Corporate Holiday on 01-Jan",
         "Critical test suite passes; unsupported narrative claim rate measured at 0%; risk register completed.", "Planned"),
        ("Week 11", "04-Jan-2027 to 08-Jan-2027", "Portfolio Scale-Up & Stakeholder Validation", "Phase 4: Scale & Handover",
         "Contingent scale-up: 30 products, 10+ materials, 4 plants, 3 DCs, 8 markets, 20 scenarios; query profiling; stakeholder dry-run",
         "Generator scales smoothly; multi-product shared material conflicts validated; stakeholder feedback ingested.", "Planned"),
        ("Week 12", "11-Jan-2027 to 18-Jan-2027", "Executive Demonstration, Handover & Archival", "Phase 4: Scale & Handover (Gate 4)",
         "Clean source repository, User Guide, Architecture Document, Executive Deck (12-15 slides), Live Showcase Demo",
         "Clean-slate installation succeeds from Git clone; live demo delivered to Director (20+ yrs) and Group Manager (27+ yrs).", "Planned")
    ]

    for idx, w in enumerate(weeks_master, start=6):
        ws2.row_dimensions[idx].height = 36
        bg = WHITE if idx % 2 != 0 else ICE_BG
        if w[6] == "Completed":
            status_fill = STATUS_GREEN_FILL
            status_text = STATUS_GREEN_TEXT
        elif w[6] == "Active":
            status_fill = STATUS_BLUE_FILL
            status_text = STATUS_BLUE_TEXT
        elif "Sign-Off" in w[6] or "Review" in w[6]:
            status_fill = STATUS_AMBER_FILL
            status_text = STATUS_AMBER_TEXT
        else:
            status_fill = STATUS_GRAY_FILL
            status_text = STATUS_GRAY_TEXT
        
        style_data_cell(ws2[f"A{idx}"], w[0], size=10, bold=True, align="center", fill_color=bg)
        style_data_cell(ws2[f"B{idx}"], w[1], size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws2[f"C{idx}"], w[2], size=10, bold=True, fill_color=bg)
        style_data_cell(ws2[f"D{idx}"], w[3], size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws2[f"E{idx}"], w[4], size=9, bold=False, fill_color=bg)
        style_data_cell(ws2[f"F{idx}"], w[5], size=9, bold=False, fill_color=bg)
        style_data_cell(ws2[f"G{idx}"], w[6], size=10, bold=True, align="center", fill_color=status_fill, text_color=status_text)

    # =========================================================================
    # TAB 3: COMPLETE 60-DAY OPERATIONAL WORK BREAKDOWN SCHEDULE
    # =========================================================================
    ws3 = wb.create_sheet(title="Day-by-Day Detailed Schedule")
    ws3.views.sheetView[0].showGridLines = True

    # Title Banner
    ws3.merge_cells("A1:J1")
    t3 = ws3["A1"]
    t3.value = "COMPLETE 60-DAY OPERATIONAL WORK BREAKDOWN SCHEDULE"
    t3.font = Font(name=font_family, size=15, bold=True, color=WHITE)
    t3.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    t3.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws3.row_dimensions[1].height = 36

    ws3.merge_cells("A2:J2")
    st3 = ws3["A2"]
    st3.value = "Phase-Wise Granular Daily Engineering Tasks, Work Products, and Governance Milestones (27-Oct-2026 to 18-Jan-2027)"
    st3.font = Font(name=font_family, size=10, italic=True, color=WHITE)
    st3.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    st3.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws3.row_dimensions[2].height = 22

    # Executive Governance Footnote / Scope Clarification Bar
    ws3.merge_cells("A3:J3")
    fn3 = ws3["A3"]
    fn3.value = "Calendar Integrity Note: Days 44 (25-Dec) and 49 (01-Jan) are scheduled Corporate Holidays / Stability Buffers. 58 Active Engineering Days + 2 Holiday Buffers = 60 Weekdays."
    fn3.font = Font(name=font_family, size=8.5, italic=True, color=NAVY_DARK)
    fn3.fill = PatternFill(start_color=NAVY_LIGHT, end_color=NAVY_LIGHT, fill_type="solid")
    fn3.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws3.row_dimensions[3].height = 20

    day_headers = ["Day #", "Date", "Day of Week", "Week #", "Phase", "Functional Workstream", "Strategic Daily Objective", "Detailed Technical Tasks & Engineering Activities", "Deliverable / Work Product", "Milestone / Status"]
    ws3.row_dimensions[5].height = 26
    d_cols = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for c, h in zip(d_cols, day_headers):
        style_header_cell(ws3[f"{c}5"], h, fill_color=NAVY_DARK, size=10)

    # 60 Weekdays calculation
    start_date = datetime.date(2026, 10, 27)
    curr_date = start_date
    calendar_days = []
    while len(calendar_days) < 60:
        if curr_date.weekday() < 5:
            calendar_days.append(curr_date)
        curr_date += datetime.timedelta(days=1)

    daily_plan = [
        # PHASE 1: FOUNDATION & DATA ARCHITECTURE (Days 1 - 14)
        # Week 1
        (1, "Phase 1: Foundation", "Project Kick-off & Master Blueprint Ingestion", 
         "Review 15-page brief; clarify synthetic boundaries; eliminate UK/India ambiguities; confirm Augmentin as illustrative demo product in parameterized Indian supply network.",
         "Project charter notes, ratified scope boundaries, workspace initialized.", "Completed"),
        (2, "Phase 1: Foundation", "End-to-End Supply Chain Process Mapping", 
         "Map 8-stage pharma lifecycle: Sourcing -> QC Retest -> Manufacturing -> Batch Release -> Logistics -> Warehousing -> Fulfilment. Delineate exact handoffs and constraints.",
         "8-stage process flow diagram, cross-functional dependency matrix.", "Completed"),
        (3, "Phase 1: Foundation", "Core Operating Principles & Terminology Formalization", 
         "Establish strict entity separation: Product Family vs Finished SKU vs Material SKU. Define Lead Time vs Cycle Time and Physical vs Eligible Inventory rules.",
         "Domain glossary document, mathematical definitions for FEFO eligibility.", "Completed"),
        (4, "Phase 1: Foundation", "Technical Architecture & Delivery Roadmap Sign-Off", 
         "Finalize 12-week schedule, directory architecture (`src/generator/`, `src/engine/`, `src/ui/`, `src/agent/`), establish tool contracts. Align with Director and Group Manager.",
         "12-Week Master Schedule Excel, ratified architectural blueprint.", "Completed"),

        # Week 2
        (5, "Data Architecture", "Master Data Entities Specification (8 Tables)", 
         "Formulate exact schemas, primary keys, and data types for `dim_product`, `dim_finished_sku`, `dim_material`, `dim_supplier`, `dim_location`, `dim_customer`, `dim_market`, `dim_production_line`.",
         "Draft master data dictionary, Pydantic schema contracts for master records.", "Completed"),
        (6, "Data Architecture", "Network Topology & Bridge Tables (4 Tables)", 
         "Define schemas for `bridge_bill_of_material` (per-unit and per-batch basis, scrap factors), `bridge_supplier_material`, `bridge_sku_market`, and `bridge_location_route`.",
         "BOM schema specification, multi-tier network connectivity matrix.", "Completed"),
        (7, "Data Architecture", "Transactional & Planning Fact Tables (9 Tables)", 
         "Specify schemas for `fact_demand_history`, `fact_customer_order`, `fact_demand_forecast`, `fact_supply_plan`, `fact_material_requirement`, `fact_inventory_projection`, `fact_purchase_order`, `fact_inventory_lot`, `fact_material_consumption`.",
         "Transactional schema specs with temporal validity and version date keys.", "Completed"),
        (8, "Data Architecture", "Manufacturing, Logistics & Risk Tables (12 Tables)", 
         "Specify schemas for `fact_production_order`, `fact_batch`, `fact_quality_event`, `fact_capacity`, `fact_shipment`, `dim_scenario`, `fact_risk_event`, `bridge_risk_evidence`, `fact_root_cause`, `fact_mitigation_simulation`, `fact_recommendation`, `dataset_manifest`.",
         "Control tower schema specification, risk-evidence relationship contract.", "Completed"),
        (9, "Data Architecture", "Entity-Relationship Diagram (ERD) Publication", 
         "Consolidate all 33 schemas into comprehensive Data Dictionary. Generate interactive visual ERD displaying primary/foreign key connections across all layers.",
         "Data Dictionary Markdown, Visual ERD diagram. Gate 1 Review Prep.", "Completed"),

        # Week 3
        (10, "Data Engineering", "Generator Architecture & Master Record Synthesizer", 
         "Implement `src/generator/master_data.py` with seeded random generator (`seed: 20261014`). Generate real Indian geography nodes with fictional company/supplier/plant entities.",
         "Master data generation module, reproducible seed configuration.", "Completed"),
        (11, "Data Engineering", "104-Week Historical Demand Generator", 
         "Implement `src/generator/demand_data.py` modeling weekly customer demand: baseline volume, trend, annual/quarterly seasonality, holiday event spikes, and controlled Gaussian noise.",
         "Historical demand dataset (104 weeks), demand variance profile report.", "Completed"),
        (12, "Data Engineering", "Supply Chain Transactions Synthesizer", 
         "Implement `src/generator/supply_data.py` generating purchase orders, inventory lots with QC status/expiry, production orders, batch genealogy, and inter-city shipments.",
         "Synthetic operational transaction generator, lot-level inventory tables.", "Completed"),
        (13, "Data Engineering", "Disruption Scenario Injection Engine", 
         "Implement `src/generator/disruption_injector.py` injecting 5 benchmark disruptions: Supplier Delay (A), Batch QA Hold (B), Shared Material Shortage (C), Expiry Exposure (D), Mitigation Feasibility (E).",
         "Disruption injection logic, ground-truth scenario registry in `dim_scenario`.", "Completed"),
        (14, "Data Engineering", "Data Integrity Test Suite & Phase 1 Parquet Export", 
         "Write automated pytest suite (`tests/test_data_integrity.py`) verifying referential integrity, date logic, non-negative stock balances. Export clean CSV, Parquet, and SQLite datasets.",
         "Phase 1 Synthetic Dataset (691 rows, 30 tables), `dataset_manifest.json`. Gate 1 Sign-off.", "Completed"),

        # PHASE 2: DETERMINISTIC ANALYTICS & CORE ENGINES (Days 15 - 34)
        # Week 4
        (15, "Core Analytics", "Lot-Level Inventory Eligibility & FEFO Allocator", 
         "Develop `src/engine/inventory.py`. Implement multi-factor eligibility filter (quarantine, blocked, expired, remaining shelf life) and strictly sort eligible lots by earliest expiry date.",
         "FEFO allocation engine, lot eligibility unit test suite.", "Completed"),
        (16, "Core Analytics", "Multi-Echelon Weekly Inventory Projection Engine", 
         "Implement recursive inventory balance calculation ($I_t = I_{t-1} + R_t + P_t - D_t$). Track projected stockouts, safety stock breaches, and unmet customer demand.",
         "Weekly inventory projection engine, multi-echelon stock trajectory module.", "Completed"),
        (17, "Core Analytics", "BOM Explosion & Material Netting Engine (MRP)", 
         "Develop `src/engine/mrp.py` converting planned finished SKU production into gross component requirements. Net against eligible material stock and confirmed incoming POs.",
         "Material requirement planning engine, component shortage detector.", "Completed"),
        (18, "Core Analytics", "Supplier OTIF & Plant Line Capacity Analytics", 
         "Develop `src/engine/analytics.py` calculating supplier on-time in-full %, lead time variance, and manufacturing line capacity utilisation % (net available vs committed hours).",
         "Supplier OTIF calculator, line capacity utilisation analytics module.", "Completed"),
        (19, "Core Analytics", "Analytics Reconciliation & Mathematical Test Suite", 
         "Build reconciliation test suite proving inventory conservation across all nodes. Ensure zero unexplained stock gains or losses across historical and future horizons.",
         "Reconciliation report, automated core calculation test suite (Integration Buffer).", "Completed"),

        # Week 5
        (20, "Forecasting Layer", "Demand Time-Series Preprocessing & Splitting", 
         "Develop `src/forecasting/prep.py`. Build time-based train/validation/test splits (104 historical weeks). Enforce strict controls against future target leakage.",
         "Time-series split pipeline, data leakage audit script.", "Completed"),
        (21, "Forecasting Layer", "Baseline Statistical Forecasting Models", 
         "Implement Seasonal Naive, Moving Average, and Exponential Smoothing (Holt-Winters) models generating 26-week horizon point forecasts.",
         "Baseline forecasting module, benchmark accuracy evaluation report.", "Completed"),
        (22, "Forecasting Layer", "ML Forecasting Models & Confidence Intervals", 
         "Implement lightweight ML forecasting model (e.g. Ridge/LightGBM) with lag features, seasonal indicators, and P10/P90 prediction interval estimation.",
         "Candidate ML forecast module, probabilistic prediction interval generator.", "Completed"),
        (23, "Forecasting Layer", "Forecast Evaluation & Versioning Engine", 
         "Implement deterministic calculation of WAPE, MAE, Forecast Bias %, and Tracking Signal. Store versioned forecasts with creation timestamps in `fact_demand_forecast`.",
         "Forecast evaluation engine, versioned forecast registry.", "Completed"),
        (24, "Forecasting Layer", "Forecast Model Card & Demand Anomaly Detector", 
         "Author official Forecast Model Card detailing training horizon, error metrics, and operational limitations. Implement threshold-based demand anomaly alert.",
         "Forecast Model Card document, demand anomaly detection service.", "Active"),

        # Week 6
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
         "Run validation tests against injected Scenarios A through E. Verify >=95% precision, 100% recall, and accurate causal chain attribution.",
         "Risk engine validation report, benchmark test results. Gate 2 Prep.", "Milestone Review"),

        # Week 7
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
        (34, "Mitigation Engine", "Multi-Criteria Recommendation Engine & Integration Buffer", 
         "Develop recommendation evaluator ranking options by shortage reduction %, synthetic cost, and feasibility (`human_approval_required = True`). Execute cross-engine integration tests.",
         "Recommendation engine, Gate 2 Technical Evaluation Report & Integration Buffer.", "Gate 2 Sign-Off"),

        # PHASE 3: AGENTIC AI ORCHESTRATION & EXPERIENCE LAYER (Days 35 - 44)
        # Week 8
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

        # Week 9
        (40, "UI & Experience", "Streamlit Multi-Page Layout & Corporate Theme", 
         "Set up Streamlit layout in `src/ui/`. Implement executive dark-navy palette, sidebar navigation, scenario selectors, and mandatory synthetic data banners.",
         "Control tower UI scaffold, responsive layout configuration.", "Planned"),
        (41, "UI & Experience", "Executive & Demand Dashboards (Pages 1 - 3)", 
         "Build Page 1: Executive Overview (KPI metric cards, priority risk queue), Page 2: Demand & Forecasting (Plotly forecast charts), Page 3: Inventory & Expiry (FEFO lot health).",
         "Pages 1-3 interactive dashboards with dynamic Plotly visualizations.", "Planned"),
        (42, "UI & Experience", "Operations & Logistics Dashboards (Pages 4 - 6)", 
         "Build Page 4: Procurement & Suppliers (open POs, OTIF gauge), Page 5: Manufacturing & Quality (line capacity heatmap, batch QA hold), Page 6: Logistics (in-transit tracking).",
         "Pages 4-6 operational dashboards with supply chain visibility.", "Planned"),
        (43, "UI & Experience", "AI Copilot, Decision-Support & Gate 3 Review", 
         "Build Pages 7-10 (Risk, Simulation, Copilot, Briefings). Complete end-to-end integration of single-product vertical slice. Pre-holiday Gate 3 executive review.",
         "10-page integrated Control Tower application. Gate 3 Milestone Review.", "Gate 3 Sign-Off"),
        (44, "Corporate Holiday", "Corporate Holiday — Christmas Day", 
         "Widely observed holiday. No operational software development scheduled. Server environment on automated standby; architecture buffer.",
         "Scheduled Corporate Holiday (Architecture & System Stability Buffer).", "Corporate Holiday"),

        # PHASE 4: SCALE-UP, RESPONSIBLE AI & HANDOVER (Days 45 - 60)
        # Week 10
        (45, "Testing & AI Ethics", "Comprehensive Data Quality & Stress Testing", 
         "Execute stress tests on edge cases: sudden demand spikes, zero-inventory nodes, expired lot hold, severe supplier stockouts, and conflicting production orders.",
         "Data stress test suite, robustness verification report.", "Planned"),
        (46, "Testing & AI Ethics", "Prompt Injection & Security Vulnerability Audit", 
         "Conduct adversarial security testing on AI assistant: test prompt injections, attempts to bypass tool-calling, and instructions to fabricate non-existent supply data.",
         "Security and prompt injection vulnerability audit report.", "Planned"),
        (47, "Testing & AI Ethics", "Factuality & Evidence Grounding Benchmark", 
         "Measure agent hallucination rate: verify 100% of numerical quantities and dates match calculated backend outputs. Confirm zero ungrounded causal claims.",
         "Factuality benchmark results, hallucination metric scorecard.", "Planned"),
        (48, "Testing & AI Ethics", "Responsible AI System Card & Testing Report", 
         "Author official Responsible AI System Card covering model boundaries, synthetic data limitations, human oversight requirements, and ethical guidelines. Consolidate CI test suite.",
         "Responsible AI System Card, Consolidated Test Report.", "Sprint Review"),
        (49, "Corporate Holiday", "Corporate Holiday — New Year's Day", 
         "Widely observed holiday. No operational software development scheduled. Automated continuous integration buffer.",
         "Scheduled Corporate Holiday (CI & Automated Test Buffer).", "Corporate Holiday"),

        # Week 11
        (50, "Scale & Refinement", "Contingent Portfolio Expansion (30 Products)", 
         "Contingent on Gate 3 approval: Scale generator configuration to 30 product families, shared excipients and APIs, 4 manufacturing plants, 3 regional DCs, 8 Indian markets, 6 suppliers.",
         "Scaled synthetic dataset (30 products), portfolio manifest.", "Planned"),
        (51, "Scale & Refinement", "Multi-Disruption Injection (20 Distinct Scenarios)", 
         "Populate all 20 scenario types from Section 10.3 (customs delays, cold-chain temperature excursions, yield drops, equipment outages, single-source failures).",
         "20 disruption scenarios dataset, scenario ground-truth registry.", "Planned"),
        (52, "Scale & Refinement", "System Performance Profiling & Query Optimization", 
         "Profile database queries and Streamlit caching (`@st.cache_data`). Ensure sub-second dashboard rendering (<=1.0s) and low memory utilisation at 30-product scale.",
         "Performance profiling report, query latency optimization patch.", "Planned"),
        (53, "Scale & Refinement", "Stakeholder Dry-Run & Interactive Walkthrough", 
         "Conduct end-to-end dry run demonstrating the core user journey: Morning Briefing -> Alert Investigation -> Root-Cause Tracing -> What-If Simulation -> Planner Approval.",
         "Stakeholder demo feedback log, prioritized backlog refinements.", "Planned"),
        (54, "Scale & Refinement", "User Feedback Ingestion & Final Polish", 
         "Implement high-priority polish items: refine UI tooltips, improve chart contrast, format executive export tables, and finalize documentation links.",
         "Polished Control Tower application ready for final executive review.", "Sprint Review"),

        # Week 12
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

    curr_row = 6
    for d_idx, (day_num, workstream, obj, tasks, output, status) in enumerate(daily_plan):
        phase_num = 1 if day_num <= 14 else (2 if day_num <= 34 else (3 if day_num <= 44 else 4))
        phase_label = f"Phase {phase_num}"
        
        # Insert Phase Divider Banner
        if day_num in [1, 15, 35, 45]:
            banner_row = curr_row
            ws3.row_dimensions[banner_row].height = 26
            ws3.merge_cells(f"A{banner_row}:J{banner_row}")
            b_cell = ws3[f"A{banner_row}"]
            
            phase_titles = {
                1: "PHASE 1: FOUNDATION & DATA ARCHITECTURE (Weeks 1 to 3 | Days 01 - 14 | 27-Oct-2026 to 13-Nov-2026)",
                15: "PHASE 2: DETERMINISTIC ANALYTICS & CORE ENGINES (Weeks 4 to 7 | Days 15 - 34 | 16-Nov-2026 to 11-Dec-2026)",
                35: "PHASE 3: AGENTIC AI ORCHESTRATION & EXPERIENCE LAYER (Weeks 8 to 9 | Days 35 - 44 | 14-Dec-2026 to 25-Dec-2026)",
                45: "PHASE 4: SCALE-UP, RESPONSIBLE AI & FINAL HANDOVER (Weeks 10 to 12 | Days 45 - 60 | 28-Dec-2026 to 18-Jan-2027)"
            }
            b_cell.value = phase_titles[day_num]
            b_cell.font = Font(name=font_family, size=11, bold=True, color=WHITE)
            b_cell.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
            b_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            b_cell.border = thin_border
            curr_row += 1

        row_num = curr_row
        ws3.row_dimensions[row_num].height = 36
        c_date = calendar_days[d_idx]
        d_str = c_date.strftime("%d-%b-%Y")
        day_name = c_date.strftime("%A")
        
        # Calculate week string
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
        elif status == "Active":
            s_fill = STATUS_BLUE_FILL
            s_text = STATUS_BLUE_TEXT
        elif status == "Corporate Holiday":
            s_fill = STATUS_PURPLE_FILL
            s_text = STATUS_PURPLE_TEXT
        else:
            s_fill = STATUS_GRAY_FILL
            s_text = STATUS_GRAY_TEXT

        style_data_cell(ws3[f"A{row_num}"], f"Day {day_num:02d}", size=10, bold=True, align="center", fill_color=bg)
        style_data_cell(ws3[f"B{row_num}"], d_str, size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws3[f"C{row_num}"], day_name, size=9, bold=False, align="center", fill_color=bg)
        style_data_cell(ws3[f"D{row_num}"], wk_str, size=9, bold=True, align="center", fill_color=bg, text_color=NAVY_MID)
        style_data_cell(ws3[f"E{row_num}"], phase_label, size=9, bold=True, align="center", fill_color=NAVY_LIGHT, text_color=NAVY_DARK)
        style_data_cell(ws3[f"F{row_num}"], workstream, size=9, bold=False, fill_color=bg)
        style_data_cell(ws3[f"G{row_num}"], obj, size=10, bold=True, fill_color=bg)
        style_data_cell(ws3[f"H{row_num}"], tasks, size=9, bold=False, fill_color=bg)
        style_data_cell(ws3[f"I{row_num}"], output, size=9, bold=False, fill_color=bg)
        style_data_cell(ws3[f"J{row_num}"], status, size=9, bold=True, align="center", fill_color=s_fill, text_color=s_text)
        
        curr_row += 1

    # Auto-adjust column widths for all 3 sheets
    for ws in [ws1, ws2, ws3]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.coordinate in ws.merged_cells:
                    continue
                if cell.value:
                    lines = str(cell.value).split("\n")
                    for line in lines:
                        if len(str(line)) > max_len:
                            max_len = len(str(line))
            if col_letter in ["A"]:
                ws.column_dimensions[col_letter].width = max(max_len + 3, 14)
            elif col_letter in ["B", "C", "D"]:
                ws.column_dimensions[col_letter].width = max(max_len + 3, 18)
            else:
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 22), 65)

    # Custom column width overrides
    ws1.column_dimensions["A"].width = 22
    ws1.column_dimensions["B"].width = 20
    ws1.column_dimensions["C"].width = 36
    ws1.column_dimensions["D"].width = 54
    ws1.column_dimensions["E"].width = 46
    ws1.column_dimensions["F"].width = 36
    ws1.column_dimensions["G"].width = 22

    ws2.column_dimensions["A"].width = 12
    ws2.column_dimensions["B"].width = 28
    ws2.column_dimensions["C"].width = 36
    ws2.column_dimensions["D"].width = 24
    ws2.column_dimensions["E"].width = 46
    ws2.column_dimensions["F"].width = 48
    ws2.column_dimensions["G"].width = 16

    ws3.column_dimensions["A"].width = 10
    ws3.column_dimensions["B"].width = 14
    ws3.column_dimensions["C"].width = 14
    ws3.column_dimensions["D"].width = 12
    ws3.column_dimensions["E"].width = 12
    ws3.column_dimensions["F"].width = 20
    ws3.column_dimensions["G"].width = 36
    ws3.column_dimensions["H"].width = 54
    ws3.column_dimensions["I"].width = 40
    ws3.column_dimensions["J"].width = 18

    # Freeze panes on data tables for executive review
    ws1.freeze_panes = 'A6'
    ws2.freeze_panes = 'A6'
    ws3.freeze_panes = 'A6'

    try:
        wb.save(filepath)
        print(f"Refined 3-Tab Workbook successfully generated and saved at: {filepath}")
    except PermissionError:
        fallback = filepath.replace(".xlsx", "_updated.xlsx")
        wb.save(fallback)
        print(f"Notice: Main workbook is locked by another program. Saved to: {fallback}")

if __name__ == "__main__":
    out_file = r"d:\AI Pharmaceutical Supply Chain\AI_Supply_Chain_Control_Tower_12_Week_Executive_Schedule.xlsx"
    generate_3tab_executive_schedule(out_file)

