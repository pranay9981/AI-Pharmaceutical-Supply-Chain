import sqlite3
import json
import os

from generate_full_assets import generate_viewers

db_json, graph_json = generate_viewers()

# HTML template generator
def build_html(is_standalone_graph=False):
    # CSS block
    css = """
        :root {
            --bg-base: #070b14;
            --bg-sidebar: #0b1120;
            --bg-card: #0f172a;
            --bg-card-hover: #1e293b;
            --border-subtle: #1e293b;
            --border-accent: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --accent-cyan: #38bdf8;
            --accent-emerald: #10b981;
            --accent-indigo: #818cf8;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --accent-purple: #c084fc;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg-base);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        /* Header */
        header {
            background: #080d1a;
            border-bottom: 1px solid var(--border-subtle);
            padding: 10px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
            gap: 16px;
            z-index: 100;
        }
        .brand-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand-icon {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #0284c7, #0369a1);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 19px;
            box-shadow: 0 0 12px rgba(2, 132, 199, 0.4);
        }
        .brand-titles h1 {
            font-size: 15px;
            font-weight: 700;
            color: #fff;
            letter-spacing: -0.01em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .brand-titles p {
            font-size: 11.5px;
            color: var(--text-muted);
            font-family: ui-monospace, monospace;
        }

        /* Top View Navigation Tabs */
        .top-nav-switcher {
            display: flex;
            align-items: center;
            background: #050811;
            padding: 3px;
            border-radius: 8px;
            border: 1px solid var(--border-accent);
            gap: 4px;
        }
        .top-nav-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 7px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.15s ease;
            text-decoration: none;
        }
        .top-nav-btn:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.05);
        }
        .top-nav-btn.active {
            background: linear-gradient(135deg, rgba(2, 132, 199, 0.3), rgba(56, 189, 248, 0.2));
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.4);
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .stat-pill {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-subtle);
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .dot.emerald { background: var(--accent-emerald); box-shadow: 0 0 8px rgba(16, 185, 129, 0.5); }
        .dot.cyan { background: var(--accent-cyan); box-shadow: 0 0 8px rgba(56, 189, 248, 0.5); }
        .dot.purple { background: var(--accent-purple); box-shadow: 0 0 8px rgba(192, 132, 252, 0.5); }

        .btn-ext-tab {
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid var(--border-accent);
            color: #38bdf8;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s;
        }
        .btn-ext-tab:hover {
            background: rgba(56, 189, 248, 0.15);
            border-color: #38bdf8;
        }

        /* Views Container */
        .view-wrapper {
            flex: 1;
            display: flex;
            overflow: hidden;
            min-height: 0;
            position: relative;
        }

        /* VIEW 1: Database Explorer */
        #app-view-db {
            width: 100%;
            height: 100%;
            display: grid;
            grid-template-columns: 320px 1fr;
            overflow: hidden;
            min-height: 0;
        }
        aside {
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .sidebar-header {
            padding: 14px 16px 10px;
            border-bottom: 1px solid var(--border-subtle);
        }
        .search-box {
            width: 100%;
            background: #080d18;
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 8px 12px;
            color: #fff;
            font-size: 13px;
            outline: none;
            transition: all 0.15s ease;
        }
        .search-box:focus {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
        }
        .tier-filter-pills {
            display: flex;
            gap: 5px;
            margin-top: 10px;
            overflow-x: auto;
            padding-bottom: 4px;
            scrollbar-width: none;
        }
        .tier-filter-pills::-webkit-scrollbar { display: none; }
        .tier-pill {
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid transparent;
            color: var(--text-muted);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.15s;
        }
        .tier-pill:hover { color: #fff; background: #1e293b; }
        .tier-pill.active {
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-cyan);
            border-color: rgba(56, 189, 248, 0.4);
            font-weight: 600;
        }
        .table-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .table-item {
            padding: 10px 12px;
            border-radius: 6px;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .table-item:hover {
            background: rgba(30, 41, 59, 0.6);
            color: #fff;
        }
        .table-item.active {
            background: rgba(6, 182, 212, 0.14);
            border-color: rgba(6, 182, 212, 0.4);
            color: var(--accent-cyan);
        }
        .table-item-name {
            font-size: 13px;
            font-family: ui-monospace, monospace;
            font-weight: 500;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 200px;
        }
        .table-item-badge {
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(30, 41, 59, 0.8);
            color: var(--text-muted);
            font-weight: 600;
        }
        .table-item.active .table-item-badge {
            background: rgba(56, 189, 248, 0.2);
            color: var(--accent-cyan);
        }

        /* Main Grid Area */
        main {
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: #080d1a;
            min-height: 0;
        }
        .table-toolbar {
            padding: 14px 20px;
            background: #0a101f;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
            gap: 16px;
            flex-wrap: wrap;
        }
        .table-meta {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .table-title {
            font-size: 18px;
            font-weight: 700;
            color: #fff;
            font-family: ui-monospace, monospace;
        }
        .tag {
            font-size: 11.5px;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
        .tag.cyan { background: rgba(56, 189, 248, 0.15); color: var(--accent-cyan); border: 1px solid rgba(56, 189, 248, 0.3); }
        .tag.emerald { background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.3); }
        .tag.purple { background: rgba(192, 132, 252, 0.15); color: var(--accent-purple); border: 1px solid rgba(192, 132, 252, 0.3); }
        .tag.amber { background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3); }
        .tag.rose { background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.3); }

        .table-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .view-mode-tabs {
            display: inline-flex;
            background: #060913;
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 3px;
            gap: 3px;
        }
        .mode-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }
        .mode-btn:hover { color: #fff; }
        .mode-btn.active {
            background: rgba(56, 189, 248, 0.2);
            color: var(--accent-cyan);
        }
        .btn-export {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            border: 1px solid #38bdf8;
            color: #fff;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s;
        }
        .btn-export:hover { opacity: 0.9; transform: translateY(-1px); }

        /* Content Panes */
        .content-pane {
            flex: 1;
            padding: 14px 20px;
            display: none;
            min-height: 0;
            overflow: hidden;
            box-sizing: border-box;
        }
        #pane-data.active,
        #pane-sql.active {
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        #pane-schema.active {
            display: block;
            overflow-y: auto;
        }

        .filter-row-bar {
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-shrink: 0;
        }
        .row-filter-input {
            background: #0a1122;
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 6px 12px;
            color: #fff;
            font-size: 12.5px;
            width: 280px;
        }
        .row-filter-input:focus {
            border-color: var(--accent-cyan);
            outline: none;
        }
        .row-count-label {
            font-size: 12px;
            color: var(--text-dim);
            flex-shrink: 0;
        }

        /* Pinned Horizontal Scrollbar Grid */
        .grid-wrapper {
            flex: 1;
            min-height: 0;
            width: 100%;
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            background: #050812;
            overflow: auto;
            position: relative;
        }
        table.data-grid {
            border-collapse: separate;
            border-spacing: 0;
            width: max-content;
            min-width: 100%;
            font-size: 12.5px;
            font-family: ui-monospace, monospace;
        }
        table.data-grid thead th {
            position: sticky;
            top: 0;
            background: #0b1224;
            color: var(--accent-cyan);
            font-weight: 600;
            padding: 10px 14px;
            text-align: left;
            border-bottom: 2px solid #1e293b;
            border-right: 1px solid #141f36;
            white-space: nowrap;
            z-index: 10;
        }
        table.data-grid tbody tr {
            transition: background 0.1s;
        }
        table.data-grid tbody tr:nth-child(even) {
            background: rgba(15, 23, 42, 0.4);
        }
        table.data-grid tbody tr:hover {
            background: rgba(56, 189, 248, 0.08);
        }
        table.data-grid tbody td {
            padding: 8px 14px;
            border-bottom: 1px solid #131c31;
            border-right: 1px solid #111a2e;
            color: #cbd5e1;
            white-space: nowrap;
            max-width: 320px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .pk-badge {
            background: rgba(245, 158, 11, 0.2);
            color: var(--accent-amber);
            border: 1px solid rgba(245, 158, 11, 0.4);
            font-size: 10px;
            padding: 1px 4px;
            border-radius: 3px;
            margin-left: 6px;
        }

        /* Schema Spec Table */
        .spec-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            background: #090e1d;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border-subtle);
            margin-bottom: 24px;
        }
        .spec-table th, .spec-table td {
            padding: 10px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-subtle);
        }
        .spec-table th { background: #0c1429; color: var(--text-muted); font-weight: 600; font-size: 12px; }
        .ddl-box {
            background: #050813;
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 16px;
            font-family: ui-monospace, monospace;
            font-size: 12px;
            color: #7dd3fc;
            overflow-x: auto;
            white-space: pre-wrap;
            line-height: 1.5;
        }

        /* SQL sandbox */
        .sql-toolbar {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 14px;
            flex-wrap: wrap;
        }
        .sql-input {
            flex: 1;
            background: #070c18;
            border: 1px solid var(--border-accent);
            border-radius: 6px;
            padding: 8px 12px;
            color: #38bdf8;
            font-family: ui-monospace, monospace;
            font-size: 13px;
            min-width: 300px;
        }
        .btn-sql-run {
            background: var(--accent-emerald);
            border: none;
            color: #000;
            font-weight: 700;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
        }
        .preset-btn {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            font-family: ui-monospace, monospace;
        }
        .preset-btn:hover { background: #1e293b; color: #fff; }

        /* VIEW 2: TRACEABILITY GRAPH */
        #app-view-graph {
            width: 100%;
            height: 100%;
            display: none;
            flex-direction: column;
            overflow: hidden;
            background: #070b14;
            min-height: 0;
        }
        .graph-top-bar {
            padding: 10px 20px;
            background: #0a1020;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
            flex-shrink: 0;
        }
        .preset-pills-group {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }
        .graph-preset-pill {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-accent);
            color: var(--text-muted);
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .graph-preset-pill:hover {
            color: #fff;
            border-color: #38bdf8;
            background: rgba(56, 189, 248, 0.1);
        }
        .graph-preset-pill.active {
            background: rgba(56, 189, 248, 0.2);
            border-color: #38bdf8;
            color: #38bdf8;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
        }
        .graph-controls {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .graph-search-input {
            background: #070c18;
            border: 1px solid var(--border-accent);
            border-radius: 6px;
            padding: 6px 12px;
            color: #fff;
            font-size: 12px;
            width: 220px;
            outline: none;
        }
        .graph-search-input:focus { border-color: var(--accent-cyan); }
        .ctrl-btn {
            background: #0f172a;
            border: 1px solid var(--border-accent);
            color: var(--text-main);
            width: 32px;
            height: 32px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            transition: all 0.15s;
        }
        .ctrl-btn:hover { background: #1e293b; color: #38bdf8; }

        /* Stage Headers */
        .graph-echelon-headers {
            display: grid;
            grid-template-columns: repeat(8, 220px);
            padding: 8px 60px;
            background: #080d1a;
            border-bottom: 1px solid #141c30;
            flex-shrink: 0;
            user-select: none;
        }
        .echelon-col-title {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-dim);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .echelon-col-title span.step-num {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
        }

        /* Graph Work Area */
        .graph-work-area {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
            min-height: 0;
        }
        .graph-canvas-container {
            flex: 1;
            overflow: hidden;
            position: relative;
            background: radial-gradient(circle at 50% 50%, #0d1527 0%, #070b14 100%);
            cursor: grab;
            user-select: none;
        }
        .graph-canvas-container:active { cursor: grabbing; }

        svg#traceability-svg {
            width: 100%;
            height: 100%;
            display: block;
        }

        /* SVG Node & Edge Styling */
        .edge-path {
            fill: none;
            stroke: #25334d;
            stroke-width: 2px;
            transition: stroke 0.25s, stroke-width 0.25s, opacity 0.25s;
        }
        .edge-path.highlight-forward {
            stroke: #38bdf8;
            stroke-width: 3.5px;
            stroke-dasharray: 6 3;
            animation: dashPulse 1s linear infinite;
        }
        .edge-path.highlight-backward {
            stroke: #c084fc;
            stroke-width: 3.5px;
            stroke-dasharray: 6 3;
            animation: dashPulseRev 1s linear infinite;
        }
        .edge-path.highlight-risk {
            stroke: #f43f5e;
            stroke-width: 3.5px;
            stroke-dasharray: 6 3;
            animation: dashPulse 0.8s linear infinite;
        }
        @keyframes dashPulse {
            from { stroke-dashoffset: 24; }
            to { stroke-dashoffset: 0; }
        }
        @keyframes dashPulseRev {
            from { stroke-dashoffset: 0; }
            to { stroke-dashoffset: 24; }
        }

        .node-group {
            cursor: pointer;
            transition: transform 0.2s ease, opacity 0.25s ease;
        }
        .node-group:hover rect.node-card {
            filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.4));
            stroke-width: 2px;
        }
        rect.node-card {
            fill: #0d1629;
            stroke: #1e293b;
            stroke-width: 1.5px;
            rx: 8;
            ry: 8;
            transition: all 0.2s ease;
        }
        .node-group.active rect.node-card {
            stroke: #38bdf8 !important;
            stroke-width: 2.5px !important;
            fill: #111e38 !important;
            filter: drop-shadow(0 0 16px rgba(56, 189, 248, 0.6)) !important;
        }
        .node-group.upstream rect.node-card {
            stroke: #c084fc !important;
            stroke-width: 2px !important;
            filter: drop-shadow(0 0 12px rgba(192, 132, 252, 0.5)) !important;
        }
        .node-group.downstream rect.node-card {
            stroke: #f59e0b !important;
            stroke-width: 2px !important;
            filter: drop-shadow(0 0 12px rgba(245, 158, 11, 0.5)) !important;
        }
        .node-group.dimmed, .edge-path.dimmed {
            opacity: 0.12 !important;
            pointer-events: none;
        }

        /* Graph Inspector Drawer */
        .graph-inspector {
            width: 360px;
            background: #090f1f;
            border-left: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            flex-shrink: 0;
            padding: 20px;
            gap: 16px;
            box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
            z-index: 20;
        }
        .inspector-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
        }
        .inspector-id {
            font-size: 13px;
            font-family: ui-monospace, monospace;
            color: #38bdf8;
            font-weight: 700;
        }
        .inspector-title {
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            margin-top: 4px;
        }
        .inspector-desc {
            font-size: 12.5px;
            color: var(--text-muted);
            line-height: 1.5;
            background: rgba(15, 23, 42, 0.6);
            padding: 10px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-subtle);
        }
        .inspector-sec-title {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-dim);
            margin-bottom: 6px;
        }
        .lineage-tags-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .lineage-tag {
            background: #0f192e;
            border: 1px solid var(--border-accent);
            color: var(--text-main);
            padding: 4px 9px;
            border-radius: 4px;
            font-size: 11px;
            font-family: ui-monospace, monospace;
            cursor: pointer;
            transition: all 0.15s;
        }
        .lineage-tag:hover {
            border-color: #38bdf8;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.1);
        }
        .btn-jump-db {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            border: 1px solid #38bdf8;
            color: #fff;
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.15s;
            margin-top: 8px;
        }
        .btn-jump-db:hover { opacity: 0.9; transform: translateY(-1px); }
    """

    # Top Tab switcher markup
    if is_standalone_graph:
        top_tabs_html = """
            <div class="top-nav-switcher">
                <a href="db_viewer.html" class="top-nav-btn">
                    <span>🗄️</span> Open Relational Database (30 Tables)
                </a>
                <button class="top-nav-btn active">
                    <span>🕸️</span> End-to-End Traceability Graph (Standalone)
                </button>
            </div>
        """
        ext_button_html = """
            <a href="db_viewer.html" class="btn-ext-tab">
                🗄️ Switch to Database Grid
            </a>
        """
    else:
        top_tabs_html = """
            <div class="top-nav-switcher">
                <button class="top-nav-btn active" id="btn-top-db" onclick="switchAppTab('db')">
                    <span>🗄️</span> Relational Database (30 Tables)
                </button>
                <button class="top-nav-btn" id="btn-top-graph" onclick="switchAppTab('graph')">
                    <span>🕸️</span> End-to-End Traceability Graph
                </button>
            </div>
        """
        ext_button_html = """
            <a href="traceability_graph.html" target="_blank" class="btn-ext-tab" title="Open Traceability Graph in separate browser window/tab">
                ↗️ Open Graph in Separate Browser Tab
            </a>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Control Tower Relational Database & Traceability Graph</title>
    <style>
{css}
    </style>
</head>
<body>
    <header>
        <div class="brand-group">
            <div class="brand-icon">🗄️</div>
            <div class="brand-titles">
                <h1>Control Tower Relational SQLite Database Viewer</h1>
                <p>data/processed/control_tower.db &bull; SQLite 3.x Engine</p>
            </div>
        </div>

        {top_tabs_html}

        <div class="header-actions">
            <div class="stat-pill"><span class="dot emerald"></span> <strong>30</strong> Tables</div>
            <div class="stat-pill"><span class="dot cyan"></span> <strong>691</strong> Records</div>
            <div class="stat-pill"><span class="dot purple"></span> <strong>100%</strong> Traceable</div>
            {ext_button_html}
        </div>
    </header>

    <div class="view-wrapper">
        <!-- VIEW 1: Database Explorer -->
        <div id="app-view-db" style="{'display:none;' if is_standalone_graph else 'display:grid;'}">
            <aside>
                <div class="sidebar-header">
                    <input type="text" class="search-box" id="table-search" placeholder="Search tables (e.g. sku, bom, lot, po, capacity)..." oninput="filterTables()">
                    <div class="tier-filter-pills">
                        <button class="tier-pill active" onclick="filterTier('ALL', this)">All (30)</button>
                        <button class="tier-pill" onclick="filterTier('T1', this)">Tier 1: Master (8)</button>
                        <button class="tier-pill" onclick="filterTier('T2', this)">Tier 2: Bridges (4)</button>
                        <button class="tier-pill" onclick="filterTier('T3', this)">Tier 3: Facts (14)</button>
                        <button class="tier-pill" onclick="filterTier('T4', this)">Tier 4: Risk (4)</button>
                    </div>
                </div>
                <div class="table-list" id="table-list-container"></div>
            </aside>

            <main>
                <div class="table-toolbar">
                    <div class="table-meta">
                        <div class="table-title" id="active-table-name">dim_product</div>
                        <span class="tag cyan" id="active-table-tier">Tier 1: Master Dimensions</span>
                        <span class="tag emerald" id="active-table-rows">1 Rows</span>
                        <span class="tag purple" id="active-table-cols">6 Columns</span>
                    </div>
                    <div class="table-actions">
                        <div class="view-mode-tabs">
                            <button class="mode-btn active" id="btn-mode-data" onclick="switchViewMode('data')">📋 Live Data Grid</button>
                            <button class="mode-btn" id="btn-mode-schema" onclick="switchViewMode('schema')">📐 Schema & DDL</button>
                            <button class="mode-btn" id="btn-mode-sql" onclick="switchViewMode('sql')">⚡ Quick Query</button>
                        </div>
                        <button class="btn-export" onclick="exportActiveTableToCsv()">
                            <span>📥</span> Export CSV
                        </button>
                    </div>
                </div>

                <!-- Pane 1: Data Grid -->
                <div class="content-pane active" id="pane-data">
                    <div class="filter-row-bar">
                        <input type="text" class="row-filter-input" id="row-filter" placeholder="Filter rows in this table..." oninput="filterRows()">
                        <div class="row-count-label" id="row-filter-count">Showing all rows</div>
                    </div>
                    <div class="grid-wrapper">
                        <table class="data-grid" id="data-table">
                            <thead id="data-table-head"></thead>
                            <tbody id="data-table-body"></tbody>
                        </table>
                    </div>
                </div>

                <!-- Pane 2: Schema & DDL -->
                <div class="content-pane" id="pane-schema">
                    <table class="spec-table">
                        <thead>
                            <tr>
                                <th>Column Name</th>
                                <th>Data Type</th>
                                <th>Primary Key</th>
                                <th>Nullable</th>
                                <th>Default</th>
                            </tr>
                        </thead>
                        <tbody id="spec-table-body"></tbody>
                    </table>
                    <div class="inspector-sec-title">SQLite DDL Schema Statement</div>
                    <pre class="ddl-box" id="ddl-box-element"></pre>
                </div>

                <!-- Pane 3: Quick Query -->
                <div class="content-pane" id="pane-sql">
                    <div class="sql-toolbar">
                        <input type="text" class="sql-input" id="sql-custom-cond" placeholder="Filter condition or search token (e.g. Hyderabad, Delayed, > 2000)...">
                        <button class="btn-sql-run" onclick="executeCustomQuery()">Run Query</button>
                    </div>
                    <div class="inspector-sec-title">Quick Query Presets</div>
                    <div id="query-presets-container" style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:14px;"></div>
                    <div class="grid-wrapper">
                        <table class="data-grid" id="sql-table">
                            <thead id="sql-table-head"></thead>
                            <tbody id="sql-table-body"></tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>

        <!-- VIEW 2: End-to-End Traceability Graph -->
        <div id="app-view-graph" style="{'display:flex;' if is_standalone_graph else 'display:none;'}">
            <div class="graph-top-bar">
                <div class="preset-pills-group">
                    <button class="graph-preset-pill active" id="pill-all" onclick="selectGraphPreset('all')">
                        🌐 All Network (33 Nodes)
                    </button>
                    <button class="graph-preset-pill" id="pill-scna" onclick="selectGraphPreset('scenario_a')">
                        🚨 Scenario A: API Delay & Stockout
                    </button>
                    <button class="graph-preset-pill" id="pill-qual" onclick="selectGraphPreset('quality')">
                        🔬 Quality Hold & Quarantine Trace
                    </button>
                    <button class="graph-preset-pill" id="pill-t10" onclick="selectGraphPreset('sku_t10')">
                        💊 Augmentin T10 Blister Strip
                    </button>
                    <button class="graph-preset-pill" id="pill-t30" onclick="selectGraphPreset('sku_t30')">
                        🍾 Augmentin T30 Bottle
                    </button>
                </div>
                <div class="graph-controls">
                    <input type="text" class="graph-search-input" id="graph-search" placeholder="Search node (e.g. PO-2026-001, Apollo)..." oninput="searchGraphNode()">
                    <button class="ctrl-btn" title="Zoom In" onclick="zoomGraph(1.2)">+</button>
                    <button class="ctrl-btn" title="Zoom Out" onclick="zoomGraph(0.8)">&minus;</button>
                    <button class="ctrl-btn" title="Reset View" onclick="resetGraphView()">⟲</button>
                </div>
            </div>

            <!-- Echelon Header Labels -->
            <div class="graph-echelon-headers">
                <div class="echelon-col-title"><span class="step-num">1</span> Suppliers</div>
                <div class="echelon-col-title"><span class="step-num">2</span> Materials</div>
                <div class="echelon-col-title"><span class="step-num">3</span> Procurement</div>
                <div class="echelon-col-title"><span class="step-num">4</span> Manufacturing & QA</div>
                <div class="echelon-col-title"><span class="step-num">5</span> Inventory Lots</div>
                <div class="echelon-col-title"><span class="step-num">6</span> Finished SKUs & DC</div>
                <div class="echelon-col-title"><span class="step-num">7</span> Markets & Orders</div>
                <div class="echelon-col-title"><span class="step-num">8</span> Control Tower AI</div>
            </div>

            <div class="graph-work-area">
                <div class="graph-canvas-container" id="graph-canvas-container">
                    <svg id="traceability-svg" viewBox="0 0 1880 720">
                        <defs>
                            <marker id="arrow-default" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                                <polygon points="0 0, 7 3.5, 0 7" fill="#334155" />
                            </marker>
                            <marker id="arrow-active" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                                <polygon points="0 0, 7 3.5, 0 7" fill="#38bdf8" />
                            </marker>
                            <marker id="arrow-risk" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                                <polygon points="0 0, 7 3.5, 0 7" fill="#f43f5e" />
                            </marker>
                            <marker id="arrow-purple" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                                <polygon points="0 0, 7 3.5, 0 7" fill="#c084fc" />
                            </marker>
                        </defs>
                        <g id="svg-transform-layer">
                            <g id="svg-edges-layer"></g>
                            <g id="svg-nodes-layer"></g>
                        </g>
                    </svg>
                </div>

                <!-- Inspector Drawer -->
                <div class="graph-inspector" id="graph-inspector">
                    <div class="inspector-header">
                        <div>
                            <div class="inspector-id" id="ins-id">PO-2026-001</div>
                            <div class="inspector-title" id="ins-title">Purchase Order 001</div>
                        </div>
                        <span class="tag amber" id="ins-status-badge">DELAYED</span>
                    </div>

                    <div class="inspector-desc" id="ins-desc">
                        150 kg API procurement order with Deccan Active Pharma. Delivery slipped +14 days due to column breakdown.
                    </div>

                    <div>
                        <div class="inspector-sec-title">Lifecycle Echelon & Entity</div>
                        <div style="font-size:12.5px; color:#cbd5e1;" id="ins-stage-label">Stage 3: Procurement Contracts</div>
                    </div>

                    <div>
                        <div class="inspector-sec-title">Direct Upstream Predecessors</div>
                        <div class="lineage-tags-list" id="ins-upstream-list"></div>
                    </div>

                    <div>
                        <div class="inspector-sec-title">Direct Downstream Impacted</div>
                        <div class="lineage-tags-list" id="ins-downstream-list"></div>
                    </div>

                    <div style="margin-top:auto;">
                        <div class="inspector-sec-title">Database Grounding</div>
                        <div style="font-size:11.5px; color:var(--text-muted); font-family:ui-monospace, monospace; margin-bottom:8px;">
                            Table: <strong style="color:#fff;" id="ins-db-table">fact_purchase_order</strong>
                        </div>
                        <button class="btn-jump-db" id="btn-ins-jump" onclick="jumpFromGraphToDb()">
                            <span>🔍</span> View in Database Grid
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const DB_DATA = {db_json};
        const GRAPH_DATA = {graph_json};
        const TABLE_NAMES = Object.keys(DB_DATA);

        let activeTableName = 'dim_product';
        let currentTierFilter = 'ALL';
        let currentViewMode = 'data';
        let currentAppTab = '{ 'graph' if is_standalone_graph else 'db' }';

        // Traceability Graph State
        let selectedNodeId = 'PO-2026-001';
        let activePreset = 'all';
        let zoomLevel = 1.0;
        let panX = 0;
        let panY = 0;
        let isDragging = false;
        let startDragX = 0;
        let startDragY = 0;

        // Init
        function initApp() {{
            renderTableList();
            selectTable(activeTableName);
            initTraceabilityGraph();
            selectGraphNode('PO-2026-001');
        }}

        function switchAppTab(tab) {{
            currentAppTab = tab;
            const dbView = document.getElementById('app-view-db');
            const graphView = document.getElementById('app-view-graph');
            const btnDb = document.getElementById('btn-top-db');
            const btnGraph = document.getElementById('btn-top-graph');

            if (tab === 'db') {{
                dbView.style.display = 'grid';
                graphView.style.display = 'none';
                if (btnDb) btnDb.classList.add('active');
                if (btnGraph) btnGraph.classList.remove('active');
            }} else {{
                dbView.style.display = 'none';
                graphView.style.display = 'flex';
                if (btnDb) btnDb.classList.remove('active');
                if (btnGraph) btnGraph.classList.add('active');
            }}
        }}

        /* TABLE EXPLORER LOGIC */
        function renderTableList() {{
            const container = document.getElementById('table-list-container');
            const search = document.getElementById('table-search').value.toLowerCase();
            container.innerHTML = '';

            TABLE_NAMES.forEach(tName => {{
                const t = DB_DATA[tName];
                if (currentTierFilter !== 'ALL' && t.tier_short !== currentTierFilter) return;
                if (search && !tName.toLowerCase().includes(search)) return;

                const item = document.createElement('div');
                item.className = 'table-item' + (tName === activeTableName ? ' active' : '');
                item.id = 'nav-tbl-' + tName;
                item.onclick = () => selectTable(tName);
                item.innerHTML = `
                    <div class="table-item-name" title="${{tName}}">${{tName}}</div>
                    <div class="table-item-badge">${{t.row_count}}r</div>
                `;
                container.appendChild(item);
            }});
        }}

        function filterTables() {{
            renderTableList();
        }}

        function filterTier(tier, btn) {{
            document.querySelectorAll('.tier-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTierFilter = tier;
            renderTableList();
        }}

        function selectTable(tName, optSearchId) {{
            activeTableName = tName;
            document.querySelectorAll('.table-item').forEach(el => el.classList.remove('active'));
            const activeNav = document.getElementById('nav-tbl-' + tName);
            if (activeNav) activeNav.classList.add('active');

            const t = DB_DATA[tName];
            if (!t) return;

            document.getElementById('active-table-name').innerText = t.name;
            document.getElementById('active-table-tier').innerText = t.tier;
            document.getElementById('active-table-rows').innerText = t.row_count + ' Rows';
            document.getElementById('active-table-cols').innerText = t.columns.length + ' Columns';

            const filterInput = document.getElementById('row-filter');
            filterInput.value = optSearchId || '';

            renderDataGrid(t.rows, t.col_names, t.columns);
            renderSchemaSpec(t.columns, t.sql);
            renderQueryPresets(tName);

            if (optSearchId) {{
                filterRows();
            }}
        }}

        function renderDataGrid(rows, colNames, columns) {{
            const thead = document.getElementById('data-table-head');
            const tbody = document.getElementById('data-table-body');
            thead.innerHTML = '';
            tbody.innerHTML = '';

            let headHtml = '<tr><th style="width:50px; text-align:center;">#</th>';
            colNames.forEach((cName, idx) => {{
                const colInfo = columns ? columns[idx] : null;
                const pkBadge = colInfo && colInfo.pk ? '<span class="pk-badge">🔑 PK</span>' : '';
                headHtml += `<th>${{cName}}${{pkBadge}}</th>`;
            }});
            headHtml += '</tr>';
            thead.innerHTML = headHtml;

            if (rows.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="${{colNames.length + 1}}" style="text-align:center; padding:30px; color:var(--text-dim);">No records in this table.</td></tr>`;
                document.getElementById('row-filter-count').innerText = '0 rows';
                return;
            }}

            let bodyHtml = '';
            rows.forEach((r, idx) => {{
                bodyHtml += `<tr><td style="color:var(--text-dim); text-align:center; font-size:11px;">${{idx + 1}}</td>`;
                r.forEach(val => {{
                    let disp = val === null ? '<span style="color:var(--text-dim); font-style:italic;">NULL</span>' : escapeHtml(String(val));
                    bodyHtml += `<td>${{disp}}</td>`;
                }});
                bodyHtml += '</tr>';
            }});
            tbody.innerHTML = bodyHtml;
            document.getElementById('row-filter-count').innerText = `Showing all ${{rows.length}} rows`;
        }}

        function filterRows() {{
            const q = document.getElementById('row-filter').value.toLowerCase();
            const t = DB_DATA[activeTableName];
            if (!t) return;

            if (!q) {{
                renderDataGrid(t.rows, t.col_names, t.columns);
                return;
            }}

            const filtered = t.rows.filter(r => {{
                return r.some(val => val !== null && String(val).toLowerCase().includes(q));
            }});

            renderDataGrid(filtered, t.col_names, t.columns);
            document.getElementById('row-filter-count').innerText = `Showing ${{filtered.length}} of ${{t.rows.length}} rows (filtered)`;
        }}

        function renderSchemaSpec(columns, sql) {{
            const tbody = document.getElementById('spec-table-body');
            tbody.innerHTML = '';
            columns.forEach(c => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong style="color:#fff; font-family:ui-monospace, monospace;">${{c.name}}</strong></td>
                    <td><span class="tag cyan">${{c.type}}</span></td>
                    <td>${{c.pk ? '<span class="tag amber">YES 🔑</span>' : '<span style="color:var(--text-dim);">No</span>'}}</td>
                    <td>${{c.notnull ? '<span class="tag rose">NOT NULL</span>' : '<span style="color:var(--text-dim);">Nullable</span>'}}</td>
                    <td><code style="color:var(--text-muted);">${{c.dflt_value !== null ? c.dflt_value : 'NULL'}}</code></td>
                `;
                tbody.appendChild(tr);
            }});
            document.getElementById('ddl-box-element').innerText = sql || `-- No CREATE TABLE statement recorded`;
        }}

        function switchViewMode(mode) {{
            currentViewMode = mode;
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.content-pane').forEach(p => p.classList.remove('active'));

            document.getElementById('btn-mode-' + mode).classList.add('active');
            document.getElementById('pane-' + mode).classList.add('active');
        }}

        function exportActiveTableToCsv() {{
            const t = DB_DATA[activeTableName];
            if (!t) return;

            let csvContent = t.col_names.join(',') + '\\n';
            t.rows.forEach(r => {{
                const rowStr = r.map(v => {{
                    if (v === null) return '';
                    let str = String(v).replace(/"/g, '""');
                    if (str.includes(',') || str.includes('\\n') || str.includes('"')) {{
                        return `"${{str}}"`;
                    }}
                    return str;
                }}).join(',');
                csvContent += rowStr + '\\n';
            }});

            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${{activeTableName}}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }}

        function renderQueryPresets(tName) {{
            const container = document.getElementById('query-presets-container');
            container.innerHTML = '';
            const presets = [
                {{ label: `SELECT * FROM ${{tName}}`, cond: '' }},
                {{ label: `LIMIT 5`, cond: 'LIMIT 5' }},
            ];

            if (tName === 'fact_demand_history') {{
                presets.push({{ label: `demand > 2000`, cond: 'demand_quantity > 2000' }});
                presets.push({{ label: `market = 'MKT-IN-HYD'`, cond: 'MKT-IN-HYD' }});
            }} else if (tName === 'fact_purchase_order') {{
                presets.push({{ label: `DELAYED POs`, cond: 'DELAYED' }});
            }} else if (tName === 'bridge_bill_of_material') {{
                presets.push({{ label: `scrap_factor >= 2.0`, cond: '2.0' }});
            }}

            presets.forEach(p => {{
                const btn = document.createElement('button');
                btn.className = 'preset-btn';
                btn.innerText = p.label;
                btn.onclick = () => {{
                    document.getElementById('sql-custom-cond').value = p.cond;
                    executeCustomQuery();
                }};
                container.appendChild(btn);
            }});
            executeCustomQuery();
        }}

        function executeCustomQuery() {{
            const cond = document.getElementById('sql-custom-cond').value.trim();
            const t = DB_DATA[activeTableName];
            if (!t) return;

            let resultRows = t.rows;
            if (cond === 'LIMIT 5') {{
                resultRows = t.rows.slice(0, 5);
            }} else if (cond) {{
                resultRows = t.rows.filter(r => {{
                    return r.some(v => v !== null && String(v).toLowerCase().includes(cond.toLowerCase()));
                }});
            }}

            const thead = document.getElementById('sql-table-head');
            const tbody = document.getElementById('sql-table-body');
            thead.innerHTML = '';
            tbody.innerHTML = '';

            let headHtml = '<tr><th style="width:50px; text-align:center;">#</th>';
            t.col_names.forEach(cn => {{ headHtml += `<th>${{cn}}</th>`; }});
            headHtml += '</tr>';
            thead.innerHTML = headHtml;

            let bodyHtml = '';
            resultRows.forEach((r, idx) => {{
                bodyHtml += `<tr><td style="color:var(--text-dim); text-align:center;">${{idx + 1}}</td>`;
                r.forEach(v => {{
                    let disp = v === null ? '<span style="color:var(--text-dim); font-style:italic;">NULL</span>' : escapeHtml(String(v));
                    bodyHtml += `<td>${{disp}}</td>`;
                }});
                bodyHtml += '</tr>';
            }});
            tbody.innerHTML = bodyHtml;
        }}

        /* TRACEABILITY GRAPH RENDERING & LOGIC */
        function initTraceabilityGraph() {{
            const nodesLayer = document.getElementById('svg-nodes-layer');
            const edgesLayer = document.getElementById('svg-edges-layer');
            nodesLayer.innerHTML = '';
            edgesLayer.innerHTML = '';

            // Map nodes for fast lookup
            const nodeMap = {{}};
            GRAPH_DATA.nodes.forEach(n => {{ nodeMap[n.id] = n; }});

            // 1. Draw Edges
            GRAPH_DATA.edges.forEach((e, idx) => {{
                const src = nodeMap[e.from];
                const dst = nodeMap[e.to];
                if (!src || !dst) return;

                const x1 = src.x + src.w;
                const y1 = src.y + (src.h / 2);
                const x2 = dst.x;
                const y2 = dst.y + (dst.h / 2);
                const dx = (x2 - x1) * 0.5;

                const pathData = `M ${{x1}} ${{y1}} C ${{x1 + dx}} ${{y1}}, ${{x2 - dx}} ${{y2}}, ${{x2}} ${{y2}}`;

                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', pathData);
                path.setAttribute('class', 'edge-path');
                path.setAttribute('id', `edge-${{src.id}}-${{dst.id}}`);
                path.setAttribute('data-from', src.id);
                path.setAttribute('data-to', dst.id);
                path.setAttribute('marker-end', 'url(#arrow-default)');
                edgesLayer.appendChild(path);
            }});

            // 2. Draw Nodes
            GRAPH_DATA.nodes.forEach(n => {{
                const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                g.setAttribute('class', 'node-group');
                g.setAttribute('id', `node-${{n.id}}`);
                g.setAttribute('transform', `translate(${{n.x}}, ${{n.y}})`);
                g.onclick = (evt) => {{
                    evt.stopPropagation();
                    selectGraphNode(n.id);
                }};

                // Status border color
                let borderColor = '#334155';
                let statusBadgeBg = 'rgba(56, 189, 248, 0.2)';
                let statusBadgeColor = '#38bdf8';

                if (n.status === 'DELAYED' || n.status === 'BLOCKED' || n.status === 'HOLD' || n.status === 'QUARANTINED') {{
                    borderColor = '#f43f5e';
                    statusBadgeBg = 'rgba(244, 63, 94, 0.2)';
                    statusBadgeColor = '#f43f5e';
                }} else if (n.status === 'NEAR_EXPIRY' || n.status === 'HIGH_RISK') {{
                    borderColor = '#f59e0b';
                    statusBadgeBg = 'rgba(245, 158, 11, 0.2)';
                    statusBadgeColor = '#f59e0b';
                }} else if (n.status === 'CRITICAL_RISK') {{
                    borderColor = '#f43f5e';
                    statusBadgeBg = 'rgba(244, 63, 94, 0.25)';
                    statusBadgeColor = '#f43f5e';
                }} else if (n.status === 'PENDING_APPROVAL') {{
                    borderColor = '#c084fc';
                    statusBadgeBg = 'rgba(192, 132, 252, 0.25)';
                    statusBadgeColor = '#c084fc';
                }} else if (n.status === 'RELEASED' || n.status === 'AVAILABLE' || n.status === 'APPROVED') {{
                    borderColor = '#10b981';
                    statusBadgeBg = 'rgba(16, 185, 129, 0.2)';
                    statusBadgeColor = '#10b981';
                }}

                g.innerHTML = `
                    <rect class="node-card" width="${{n.w}}" height="${{n.h}}" stroke="${{borderColor}}"></rect>
                    
                    <!-- Icon & ID -->
                    <text x="10" y="22" font-size="13">${{n.icon}}</text>
                    <text x="28" y="22" font-size="11" font-weight="700" fill="#94a3b8" font-family="ui-monospace, monospace">${{n.id}}</text>
                    
                    <!-- Status Badge -->
                    <rect x="${{n.w - 74}}" y="10" width="66" height="16" rx="4" ry="4" fill="${{statusBadgeBg}}" />
                    <text x="${{n.w - 41}}" y="22" font-size="9" font-weight="700" fill="${{statusBadgeColor}}" text-anchor="middle" font-family="ui-monospace, monospace">${{n.status}}</text>

                    <!-- Title -->
                    <text x="10" y="44" font-size="12" font-weight="700" fill="#f8fafc">${{escapeHtml(n.name)}}</text>

                    <!-- Subtitle -->
                    <text x="10" y="60" font-size="10" fill="#64748b">${{escapeHtml(n.sub)}}</text>
                `;

                nodesLayer.appendChild(g);
            }});

            setupCanvasPanZoom();
        }}

        function selectGraphNode(nodeId) {{
            selectedNodeId = nodeId;
            const nodeMap = {{}};
            GRAPH_DATA.nodes.forEach(n => {{ nodeMap[n.id] = n; }});
            const node = nodeMap[nodeId];
            if (!node) return;

            // Find recursive upstream (predecessors)
            const upstreamIds = new Set();
            function traceUp(currId) {{
                GRAPH_DATA.edges.forEach(e => {{
                    if (e.to === currId && !upstreamIds.has(e.from)) {{
                        upstreamIds.add(e.from);
                        traceUp(e.from);
                    }}
                }});
            }}
            traceUp(nodeId);

            // Find recursive downstream (dependents)
            const downstreamIds = new Set();
            function traceDown(currId) {{
                GRAPH_DATA.edges.forEach(e => {{
                    if (e.from === currId && !downstreamIds.has(e.to)) {{
                        downstreamIds.add(e.to);
                        traceDown(e.to);
                    }}
                }});
            }}
            traceDown(nodeId);

            const connectedNodes = new Set([nodeId, ...upstreamIds, ...downstreamIds]);

            // Update SVG nodes
            document.querySelectorAll('.node-group').forEach(el => {{
                const id = el.id.replace('node-', '');
                el.classList.remove('active', 'upstream', 'downstream', 'dimmed');

                if (id === nodeId) {{
                    el.classList.add('active');
                }} else if (upstreamIds.has(id)) {{
                    el.classList.add('upstream');
                }} else if (downstreamIds.has(id)) {{
                    el.classList.add('downstream');
                }} else {{
                    el.classList.add('dimmed');
                }}
            }});

            // Update SVG edges
            document.querySelectorAll('.edge-path').forEach(el => {{
                const fromId = el.getAttribute('data-from');
                const toId = el.getAttribute('data-to');
                el.classList.remove('highlight-forward', 'highlight-backward', 'highlight-risk', 'dimmed');

                if (upstreamIds.has(fromId) && (upstreamIds.has(toId) || toId === nodeId)) {{
                    el.classList.add('highlight-backward');
                    el.setAttribute('marker-end', 'url(#arrow-purple)');
                }} else if ((fromId === nodeId || downstreamIds.has(fromId)) && downstreamIds.has(toId)) {{
                    el.classList.add('highlight-forward');
                    el.setAttribute('marker-end', 'url(#arrow-active)');
                }} else {{
                    el.classList.add('dimmed');
                    el.setAttribute('marker-end', 'url(#arrow-default)');
                }}
            }});

            // Update Inspector Panel
            document.getElementById('ins-id').innerText = node.id;
            document.getElementById('ins-title').innerText = node.name;
            document.getElementById('ins-desc').innerText = node.desc || node.sub;
            document.getElementById('ins-stage-label').innerText = node.stage;
            document.getElementById('ins-db-table').innerText = node.table;

            const badge = document.getElementById('ins-status-badge');
            badge.innerText = node.status;
            badge.className = 'tag ' + (node.status === 'DELAYED' || node.status === 'HOLD' || node.status === 'QUARANTINED' || node.status === 'CRITICAL_RISK' ? 'rose' : (node.status === 'RELEASED' ? 'emerald' : 'cyan'));

            // Render Upstream badges
            const upContainer = document.getElementById('ins-upstream-list');
            upContainer.innerHTML = '';
            if (upstreamIds.size === 0) {{
                upContainer.innerHTML = '<span style="color:var(--text-dim); font-size:12px;">Origin Source Entity (No Upstream)</span>';
            }} else {{
                upstreamIds.forEach(uid => {{
                    const pill = document.createElement('span');
                    pill.className = 'lineage-tag';
                    pill.innerText = '⬅ ' + uid;
                    pill.onclick = () => selectGraphNode(uid);
                    upContainer.appendChild(pill);
                }});
            }}

            // Render Downstream badges
            const downContainer = document.getElementById('ins-downstream-list');
            downContainer.innerHTML = '';
            if (downstreamIds.size === 0) {{
                downContainer.innerHTML = '<span style="color:var(--text-dim); font-size:12px;">Terminal Execution Node (No Downstream)</span>';
            }} else {{
                downstreamIds.forEach(did => {{
                    const pill = document.createElement('span');
                    pill.className = 'lineage-tag';
                    pill.innerText = did + ' ➡';
                    pill.onclick = () => selectGraphNode(did);
                    downContainer.appendChild(pill);
                }});
            }}
        }}

        function selectGraphPreset(preset) {{
            activePreset = preset;
            document.querySelectorAll('.graph-preset-pill').forEach(p => p.classList.remove('active'));
            const pBtn = document.getElementById('pill-' + (preset === 'scenario_a' ? 'scna' : (preset === 'quality' ? 'qual' : (preset === 'sku_t10' ? 't10' : (preset === 'sku_t30' ? 't30' : 'all')))));
            if (pBtn) pBtn.classList.add('active');

            if (preset === 'all') {{
                document.querySelectorAll('.node-group').forEach(el => el.classList.remove('active', 'upstream', 'downstream', 'dimmed'));
                document.querySelectorAll('.edge-path').forEach(el => {{
                    el.classList.remove('highlight-forward', 'highlight-backward', 'highlight-risk', 'dimmed');
                    el.setAttribute('marker-end', 'url(#arrow-default)');
                }});
                selectGraphNode('PO-2026-001');
                return;
            }}

            if (preset === 'scenario_a') {{
                // Highlight full chain: SUP-001 -> MAT-API-001 -> PO-2026-001 -> RISK-2026-001 -> PROD-2026-001 -> RISK-2026-002 -> RC-2026-001 -> REC-2026-001
                selectGraphNode('PO-2026-001');
            }} else if (preset === 'quality') {{
                selectGraphNode('QEV-2026-002');
            }} else if (preset === 'sku_t10') {{
                selectGraphNode('SKU-AUG-500-T10');
            }} else if (preset === 'sku_t30') {{
                selectGraphNode('SKU-AUG-500-T30');
            }}
        }}

        function searchGraphNode() {{
            const q = document.getElementById('graph-search').value.toLowerCase().trim();
            if (!q) return;

            const match = GRAPH_DATA.nodes.find(n => n.id.toLowerCase().includes(q) || n.name.toLowerCase().includes(q) || n.sub.toLowerCase().includes(q));
            if (match) {{
                selectGraphNode(match.id);
            }}
        }}

        function jumpFromGraphToDb() {{
            const node = GRAPH_DATA.nodes.find(n => n.id === selectedNodeId);
            if (!node || !node.table) return;

            switchAppTab('db');
            selectTable(node.table, node.id);
        }}

        /* PAN & ZOOM */
        function setupCanvasPanZoom() {{
            const container = document.getElementById('graph-canvas-container');
            const layer = document.getElementById('svg-transform-layer');

            container.addEventListener('mousedown', (e) => {{
                if (e.target.closest('.node-group')) return;
                isDragging = true;
                startDragX = e.clientX - panX;
                startDragY = e.clientY - panY;
            }});

            window.addEventListener('mousemove', (e) => {{
                if (!isDragging) return;
                panX = e.clientX - startDragX;
                panY = e.clientY - startDragY;
                applyTransform();
            }});

            window.addEventListener('mouseup', () => {{
                isDragging = false;
            }});

            container.addEventListener('wheel', (e) => {{
                e.preventDefault();
                const delta = e.deltaY < 0 ? 1.1 : 0.9;
                zoomLevel = Math.max(0.4, Math.min(2.5, zoomLevel * delta));
                applyTransform();
            }});
        }}

        function zoomGraph(factor) {{
            zoomLevel = Math.max(0.4, Math.min(2.5, zoomLevel * factor));
            applyTransform();
        }}

        function resetGraphView() {{
            zoomLevel = 1.0;
            panX = 0;
            panY = 0;
            applyTransform();
        }}

        function applyTransform() {{
            const layer = document.getElementById('svg-transform-layer');
            layer.setAttribute('transform', `translate(${{panX}}, ${{panY}}) scale(${{zoomLevel}})`);
        }}

        function escapeHtml(text) {{
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }}

        window.onload = initApp;
    </script>
</body>
</html>
    """
    return html

# Write db_viewer.html
db_viewer_html = build_html(is_standalone_graph=False)
with open('db_viewer.html', 'w', encoding='utf-8') as f:
    f.write(db_viewer_html)
print(f"Generated db_viewer.html (Size: {len(db_viewer_html)} bytes)")

# Write traceability_graph.html (standalone)
trace_graph_html = build_html(is_standalone_graph=True)
with open('traceability_graph.html', 'w', encoding='utf-8') as f:
    f.write(trace_graph_html)
print(f"Generated traceability_graph.html (Size: {len(trace_graph_html)} bytes)")
