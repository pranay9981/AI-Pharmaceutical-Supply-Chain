import os
import json
import sqlite3
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DB_PATH = "data/processed/control_tower.db"
EXCEL_OUT = "data/processed/control_tower_full_database.xlsx"
HTML_OUT = "docs/database_viewer.html"

def export_to_excel():
    print(f"Generating full database Excel workbook: {EXCEL_OUT}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    # Fonts & Styles
    font_family = "Segoe UI"
    NAVY_DARK = "1B365D"
    NAVY_MID = "2F5597"
    ICE_BG = "F2F5F9"
    WHITE = "FFFFFF"
    GRAY_LIGHT = "D9D9D9"

    thin_border = Border(
        left=Side(style='thin', color=GRAY_LIGHT),
        right=Side(style='thin', color=GRAY_LIGHT),
        top=Side(style='thin', color=GRAY_LIGHT),
        bottom=Side(style='thin', color=GRAY_LIGHT)
    )

    # Sheet 1: Index Sheet
    ws_index = wb.create_sheet(title="Table of Contents")
    ws_index.views.sheetView[0].showGridLines = True

    # Title
    ws_index.merge_cells("A1:E1")
    title_cell = ws_index["A1"]
    title_cell.value = "CONTROL TOWER DATABASE EXPLORER (30 RELATIONAL TABLES)"
    title_cell.font = Font(name=font_family, size=15, bold=True, color=WHITE)
    title_cell.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
    title_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_index.row_dimensions[1].height = 36

    ws_index.merge_cells("A2:E2")
    sub = ws_index["A2"]
    sub.value = "Click on any table name below to jump directly to its complete data worksheet."
    sub.font = Font(name=font_family, size=10, italic=True, color=WHITE)
    sub.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
    sub.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_index.row_dimensions[2].height = 22

    idx_headers = ["#", "Table Name", "Entity Layer", "Row Count", "Quick Link"]
    ws_index.row_dimensions[4].height = 25
    cols = ["A", "B", "C", "D", "E"]
    for c, h in zip(cols, idx_headers):
        cell = ws_index[f"{c}4"]
        cell.value = h
        cell.font = Font(name=font_family, size=10, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_DARK, end_color=NAVY_DARK, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_counts = {}
    for idx, tbl in enumerate(tables, start=1):
        df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
        row_counts[tbl] = len(df)
        
        # Categorize layer
        if tbl.startswith("dim_"):
            layer = "Master Data"
        elif tbl.startswith("bridge_"):
            layer = "Bridge / Relationship"
        elif "risk" in tbl or "root_cause" in tbl or "mitigation" in tbl or "recommendation" in tbl:
            layer = "Control Tower Output"
        elif "forecast" in tbl or "plan" in tbl or "requirement" in tbl or "capacity" in tbl:
            layer = "Planning & Supply"
        else:
            layer = "Operational Transaction"

        # Safe Excel sheet name (max 31 chars)
        sheet_title = tbl[:31]
        
        # Add to index sheet
        r_num = idx + 4
        ws_index.row_dimensions[r_num].height = 20
        bg = WHITE if idx % 2 != 0 else ICE_BG
        
        ws_index[f"A{r_num}"] = idx
        ws_index[f"A{r_num}"].alignment = Alignment(horizontal="center", vertical="center")
        ws_index[f"A{r_num}"].font = Font(name=font_family, size=10)
        ws_index[f"A{r_num}"].fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        ws_index[f"A{r_num}"].border = thin_border

        ws_index[f"B{r_num}"] = tbl
        ws_index[f"B{r_num}"].font = Font(name=font_family, size=10, bold=True)
        ws_index[f"B{r_num}"].fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        ws_index[f"B{r_num}"].border = thin_border

        ws_index[f"C{r_num}"] = layer
        ws_index[f"C{r_num}"].alignment = Alignment(horizontal="center", vertical="center")
        ws_index[f"C{r_num}"].font = Font(name=font_family, size=9)
        ws_index[f"C{r_num}"].fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        ws_index[f"C{r_num}"].border = thin_border

        ws_index[f"D{r_num}"] = len(df)
        ws_index[f"D{r_num}"].alignment = Alignment(horizontal="right", vertical="center")
        ws_index[f"D{r_num}"].font = Font(name=font_family, size=10, bold=True)
        ws_index[f"D{r_num}"].fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        ws_index[f"D{r_num}"].border = thin_border

        link_cell = ws_index[f"E{r_num}"]
        link_cell.value = f"View {tbl} ➔"
        link_cell.hyperlink = f"#'{sheet_title}'!A1"
        link_cell.font = Font(name=font_family, size=10, bold=True, color="0000FF", underline="single")
        link_cell.alignment = Alignment(horizontal="center", vertical="center")
        link_cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        link_cell.border = thin_border

        # Create Table Sheet
        ws_tbl = wb.create_sheet(title=sheet_title)
        ws_tbl.views.sheetView[0].showGridLines = True
        
        # Banner
        ws_tbl["A1"] = f"TABLE: {tbl.upper()} ({len(df)} records)"
        ws_tbl["A1"].font = Font(name=font_family, size=12, bold=True, color=NAVY_DARK)
        
        # Back link
        back_cell = ws_tbl["C1"]
        back_cell.value = "⬅ Back to Table of Contents"
        back_cell.hyperlink = "#'Table of Contents'!A1"
        back_cell.font = Font(name=font_family, size=10, bold=True, color="0000FF", underline="single")
        ws_tbl.row_dimensions[1].height = 25

        # Table Headers
        headers = list(df.columns)
        ws_tbl.row_dimensions[3].height = 24
        for c_idx, col_name in enumerate(headers, start=1):
            c_letter = get_column_letter(c_idx)
            c = ws_tbl[f"{c_letter}3"]
            c.value = col_name
            c.font = Font(name=font_family, size=10, bold=True, color=WHITE)
            c.fill = PatternFill(start_color=NAVY_MID, end_color=NAVY_MID, fill_type="solid")
            c.alignment = Alignment(horizontal="center", vertical="center")

        # Table Data
        for r_idx, row in df.iterrows():
            excel_r = r_idx + 4
            ws_tbl.row_dimensions[excel_r].height = 20
            row_bg = WHITE if r_idx % 2 == 0 else ICE_BG
            for c_idx, val in enumerate(row, start=1):
                c_letter = get_column_letter(c_idx)
                cell = ws_tbl[f"{c_letter}{excel_r}"]
                # Handle dates and booleans
                cell.value = str(val) if val is not None else ""
                cell.font = Font(name=font_family, size=9)
                cell.fill = PatternFill(start_color=row_bg, end_color=row_bg, fill_type="solid")
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="left", vertical="center")

        # Freeze Panes
        ws_tbl.freeze_panes = "A4"

        # Auto-fit columns
        for col in ws_tbl.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws_tbl.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

    # Auto-fit Index sheet
    ws_index.column_dimensions["A"].width = 6
    ws_index.column_dimensions["B"].width = 32
    ws_index.column_dimensions["C"].width = 24
    ws_index.column_dimensions["D"].width = 14
    ws_index.column_dimensions["E"].width = 28

    wb.save(EXCEL_OUT)
    conn.close()
    print(f"Excel database export completed with {len(tables)} sheets!")

def export_to_html_viewer():
    print(f"Generating interactive web browser viewer: {HTML_OUT}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]

    db_json = {}
    for tbl in tables:
        df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
        db_json[tbl] = {
            "columns": list(df.columns),
            "rows": df.astype(str).values.tolist(),
            "count": len(df)
        }
    conn.close()

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Control Tower Database Explorer</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; height: 100vh; display: flex; flex-direction: column; }}
        header {{ background: #1b365d; color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #3b82f6; }}
        header h1 {{ font-size: 18px; font-weight: 600; }}
        header .badge {{ background: #2f5597; padding: 4px 10px; border-radius: 9999px; font-size: 12px; }}
        .main-container {{ display: flex; flex: 1; overflow: hidden; }}
        sidebar {{ width: 320px; background: white; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; }}
        .search-box {{ padding: 12px; border-bottom: 1px solid #e2e8f0; }}
        .search-box input {{ width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }}
        .table-list {{ flex: 1; overflow-y: auto; }}
        .table-item {{ padding: 10px 16px; border-bottom: 1px solid #f1f5f9; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 13px; transition: background 0.15s; }}
        .table-item:hover {{ background: #f1f5f9; }}
        .table-item.active {{ background: #eff6ff; border-left: 4px solid #3b82f6; font-weight: 600; color: #1d4ed8; }}
        .table-item .cnt {{ background: #e2e8f0; padding: 2px 8px; border-radius: 12px; font-size: 11px; color: #475569; }}
        content {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; background: white; }}
        .content-header {{ padding: 16px 24px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; background: #fff; }}
        .content-header h2 {{ font-size: 16px; font-weight: 600; color: #0f172a; }}
        .table-container {{ flex: 1; overflow: auto; padding: 16px 24px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }}
        th {{ background: #f8fafc; color: #475569; font-weight: 600; padding: 10px 12px; border: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 10; }}
        td {{ padding: 8px 12px; border: 1px solid #e2e8f0; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        tr:hover {{ background: #f1f5f9; }}
    </style>
</head>
<body>
    <header>
        <div>
            <h1>Control Tower Database Explorer (SQLite)</h1>
            <p style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Database: control_tower.db | 30 Tables | Synthetic Pharmaceutical Supply Chain</p>
        </div>
        <div class="badge">691 Total Records</div>
    </header>
    <div class="main-container">
        <sidebar>
            <div class="search-box">
                <input type="text" id="searchTable" placeholder="Filter tables..." onkeyup="filterTables()">
            </div>
            <div class="table-list" id="tableList"></div>
        </sidebar>
        <content>
            <div class="content-header">
                <div>
                    <h2 id="currentTableName">Select a table</h2>
                    <span id="currentTableStats" style="font-size: 12px; color: #64748b;"></span>
                </div>
            </div>
            <div class="table-container" id="tableContainer">
                <p style="color: #64748b; font-size: 13px;">Select any table from the sidebar to view rows.</p>
            </div>
        </content>
    </div>

    <script>
        const dbData = {json.dumps(db_json)};
        let activeTable = Object.keys(dbData)[0];

        function renderSidebar() {{
            const list = document.getElementById('tableList');
            list.innerHTML = '';
            for (const tbl in dbData) {{
                const item = document.createElement('div');
                item.className = 'table-item' + (tbl === activeTable ? ' active' : '');
                item.id = 'item-' + tbl;
                item.onclick = () => showTable(tbl);
                item.innerHTML = `<span>${{tbl}}</span><span class="cnt">${{dbData[tbl].count}}</span>`;
                list.appendChild(item);
            }}
        }}

        function showTable(tbl) {{
            activeTable = tbl;
            document.querySelectorAll('.table-item').forEach(el => el.classList.remove('active'));
            const activeEl = document.getElementById('item-' + tbl);
            if (activeEl) activeEl.classList.add('active');

            document.getElementById('currentTableName').innerText = tbl;
            document.getElementById('currentTableStats').innerText = `${{dbData[tbl].count}} rows | ${{dbData[tbl].columns.length}} columns`;

            const container = document.getElementById('tableContainer');
            const data = dbData[tbl];
            if (data.rows.length === 0) {{
                container.innerHTML = '<p style="color: #64748b;">This table has 0 rows.</p>';
                return;
            }}

            let html = '<table><thead><tr>';
            for (const col of data.columns) {{
                html += `<th>${{col}}</th>`;
            }}
            html += '</tr></thead><tbody>';

            for (const row of data.rows) {{
                html += '<tr>';
                for (const cell of row) {{
                    html += `<td title="${{cell}}">${{cell}}</td>`;
                }}
                html += '</tr>';
            }}
            html += '</tbody></table>';
            container.innerHTML = html;
        }}

        function filterTables() {{
            const q = document.getElementById('searchTable').value.toLowerCase();
            document.querySelectorAll('.table-item').forEach(el => {{
                const name = el.querySelector('span').innerText.toLowerCase();
                el.style.display = name.includes(q) ? 'flex' : 'none';
            }});
        }}

        renderSidebar();
        if (activeTable) showTable(activeTable);
    </script>
</body>
</html>
"""
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML database viewer successfully created: {HTML_OUT}")

if __name__ == "__main__":
    export_to_excel()
    export_to_html_viewer()

