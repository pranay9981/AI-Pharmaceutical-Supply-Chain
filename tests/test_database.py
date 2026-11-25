import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from control_tower.database import DISCLAIMER, connect_database, initialize_database, market_supply_trace


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        workspace = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(workspace) / "demo.sqlite3"
        initialize_database(self.path, sample=True)
        self.connection = self.enterContext(closing(connect_database(self.path)))

    def test_sample_has_metadata_and_passes_sqlite_integrity_checks(self):
        metadata = self.connection.execute(
            "SELECT dataset_version, synthetic, disclaimer FROM dataset"
        ).fetchone()
        self.assertEqual(tuple(metadata), ("week-2-sample-v1", 1, DISCLAIMER))
        self.assertEqual(self.connection.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(self.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(self.connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_market_trace_resolves_both_materials_and_the_two_shipment_legs(self):
        api, packaging = market_supply_trace(self.connection, "DEMO-SHIP-MKT")
        self.assertEqual(api["market_id"], "DEMO-MKT-01")
        self.assertEqual(api["upstream_shipment_id"], "DEMO-SHIP-DC")
        self.assertEqual(api["batch_id"], "DEMO-BATCH-01")
        self.assertEqual(api["production_order_id"], "DEMO-PROD-01")
        self.assertEqual((api["requirement_id"], api["purchase_order_id"], api["supplier_id"]),
                         ("DEMO-REQ-API", "DEMO-PO-01", "DEMO-SUP-API"))
        self.assertEqual((packaging["requirement_id"], packaging["purchase_order_id"]),
                         ("DEMO-REQ-PKG", "DEMO-PO-PKG"))
        self.assertEqual(market_supply_trace(self.connection, "DEMO-SHIP-DC"), [])

    def test_scenario_override_is_parameterized_and_isolated(self):
        query = """
            SELECT scenario_id, purchase_order_id, delay_days, scenario_expected_delivery_on
            FROM scenario_purchase_order ORDER BY scenario_id, purchase_order_id
        """
        self.assertEqual([tuple(row) for row in self.connection.execute(query)], [
            ("DEMO-API-DELAY", "DEMO-PO-01", 14, "2026-11-16"),
            ("DEMO-API-DELAY", "DEMO-PO-PKG", 0, "2026-10-26"),
            ("DEMO-BASE", "DEMO-PO-01", 0, "2026-11-02"),
            ("DEMO-BASE", "DEMO-PO-PKG", 0, "2026-10-26"),
        ])
        for days, expected in ((0, "2026-11-02"), (10, "2026-11-12")):
            with self.subTest(delay_days=days):
                self.connection.execute(
                    "UPDATE api_receipt_delay SET delay_days = ? WHERE scenario_id = 'DEMO-API-DELAY'",
                    (days,),
                )
                self.assertEqual(self.connection.execute(query).fetchone()[3], expected)
        current = self.connection.execute(
            "SELECT expected_delivery_on FROM purchase_order WHERE purchase_order_id = 'DEMO-PO-01'"
        ).fetchone()[0]
        self.assertEqual(current, "2026-11-02")

    def test_wrong_entity_or_material_relationships_are_rejected(self):
        invalid_sql = (
            "UPDATE api_receipt_delay SET delay_days = -1",
            "UPDATE api_receipt_delay SET purchase_order_id = 'DEMO-PO-PKG', material_id = 'DEMO-PKG-10'",
            "UPDATE api_receipt_delay SET scenario_id = 'DEMO-BASE'",
            """
            INSERT INTO requirement_purchase_order VALUES
                ('DEMO-REQ-API', 'DEMO-PO-PKG', 'DEMO-API-01', 'DEMO-PLANT-01')
            """,
            "UPDATE production_line SET plant_id = 'DEMO-MKT-01'",
            "UPDATE shipment SET origin_id = 'DEMO-PLANT-01' WHERE shipment_id = 'DEMO-SHIP-MKT'",
        )
        for sql in invalid_sql:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                self.connection.execute(sql)

    def test_invalid_dates_quantities_and_forecast_ranges_are_rejected(self):
        invalid_sql = (
            "UPDATE purchase_order SET expected_delivery_on = '2026-11-31'",
            "UPDATE purchase_order SET expected_delivery_on = '2026-10-01'",
            "UPDATE demand_history SET week_start = '2026-10-27' WHERE week_start = '2026-10-26'",
            "UPDATE inventory_lot SET expiry_on = manufactured_on",
            "UPDATE inventory_snapshot SET reserved = on_hand, blocked = 1",
            "UPDATE shipment SET expected_arrival_on = '2026-11-15'",
            "UPDATE demand_forecast SET lower_packs = 110, upper_packs = 90",
            "UPDATE demand_forecast SET override_packs = 110",
        )
        for sql in invalid_sql:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                self.connection.execute(sql)

    def test_projection_and_risk_outputs_have_consistent_run_grain(self):
        self.connection.execute(
            "INSERT INTO planning_run VALUES ('RUN-01', 'DEMO-API-DELAY', 'DEMO-FCST-01', '2026-11-01', NULL)"
        )
        projection = """
            INSERT INTO inventory_projection (
                projection_id, run_id, sku_id, market_id, week_start, opening_packs, receipt_packs,
                demand_packs, fulfilled_packs, safety_stock_packs
            ) VALUES (?, 'RUN-01', 'DEMO-SKU-10', 'DEMO-MKT-01', '2026-11-16', 60, 0, 100, 60, 50)
        """
        self.connection.execute(projection, ("PROJECTION-01",))
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(projection, ("DUPLICATE",))
        ending, unserved = self.connection.execute(
            "SELECT ending_packs, unserved_packs FROM inventory_projection"
        ).fetchone()
        self.assertEqual((ending, unserved), (0, 40))
        self.connection.execute("""
            INSERT INTO risk_event (
                risk_id, run_id, sku_id, market_id, risk_type, status, severity, days_to_impact, shortage_packs,
                shortage_severity, timing_severity, medicine_criticality, source_dependency,
                forecast_uncertainty, recovery_difficulty
            ) VALUES ('RISK-01', 'RUN-01', 'DEMO-SKU-10', 'DEMO-MKT-01', 'STOCKOUT', 'OPEN', 'HIGH', 15, 40,
                      100, 50, 100, 100, 0, 50)
        """)
        self.assertEqual(self.connection.execute("SELECT risk_score FROM risk_event").fetchone()[0], 75)
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("""
                INSERT INTO risk_evidence (evidence_id, risk_id, run_id, role, purchase_order_id, projection_id)
                VALUES ('EV-01', 'RISK-01', 'RUN-01', 'DRIVER', 'DEMO-PO-01', 'PROJECTION-01')
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("""
                INSERT INTO recommendation (
                    recommendation_id, risk_id, action_type, feasibility, constraints_json, assumptions_json,
                    human_approval_required
                ) VALUES ('REC-01', 'RISK-01', 'EXPEDITE', 'FEASIBLE', '{}', '{}', 0)
            """)

    def test_initializing_an_existing_database_does_not_modify_it(self):
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            initialize_database(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_initialization_does_not_leave_a_partial_file(self):
        sample = self.path.with_name("invalid.sql")
        sample.write_text("INSERT INTO unknown_table VALUES (1);", encoding="utf-8")
        target = self.path.with_name("invalid.sqlite3")
        with patch("control_tower.database.SAMPLE", sample), self.assertRaises(sqlite3.OperationalError):
            initialize_database(target, sample=True)
        self.assertFalse(target.exists())

    def test_schema_only_initialization_and_read_only_connection(self):
        target = self.path.with_name("empty.sqlite3")
        initialize_database(target)
        with closing(connect_database(target, read_only=True)) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM product").fetchone()[0], 0)
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM dataset")
