-- Synthetic data for demonstration only. Not for operational decision making.
-- Small relational fixture. Week 3 will generate the full network.

UPDATE dataset SET dataset_version = 'week-2-sample-v1' WHERE singleton = 1;

INSERT INTO product VALUES ('DEMO-PROD-FAMILY', 'Velunexa', 'Demo therapy area', 'Tablet', 'MATURE', 1);
INSERT INTO sku VALUES
    ('DEMO-SKU-10', 'DEMO-PROD-FAMILY', 10, 365, 'AMBIENT', 1200, 'INR'),
    ('DEMO-SKU-30', 'DEMO-PROD-FAMILY', 30, 365, 'AMBIENT', 2800, 'INR');

INSERT INTO location VALUES
    ('DEMO-PLANT-01', 'Demo Ridge Plant', 'PLANT', 'North', 10000, 0),
    ('DEMO-DC-01', 'Demo Lake Distribution Centre', 'DC', 'North', 10000, 0),
    ('DEMO-MKT-01', 'Demo Lake Market', 'MARKET', 'North', 10000, 0);
INSERT INTO market (market_id, service_priority) VALUES ('DEMO-MKT-01', 'HIGH');
INSERT INTO production_line (line_id, plant_id, name) VALUES ('DEMO-LINE-01', 'DEMO-PLANT-01', 'Demo Packing Line');
INSERT INTO supplier VALUES
    ('DEMO-SUP-API', 'Demo Veluna Materials', 'MATERIAL', 95.0, 'HIGH'),
    ('DEMO-SUP-PKG', 'Demo Hallow Packworks', 'MATERIAL', 97.0, 'LOW');
INSERT INTO material VALUES
    ('DEMO-API-01', 'Demo Active Material', 'API', 'KG', 365, 0, 1, 1),
    ('DEMO-PKG-10', 'Demo Carton for Pack of 10', 'PACKAGING', 'EACH', 540, 0, 0, 0),
    ('DEMO-PKG-30', 'Demo Carton for Pack of 30', 'PACKAGING', 'EACH', 540, 0, 0, 0);
INSERT INTO supplier_material VALUES
    ('DEMO-SUP-API', 'DEMO-API-01', 21, 50, 1),
    ('DEMO-SUP-PKG', 'DEMO-PKG-10', 10, 100, 1),
    ('DEMO-SUP-PKG', 'DEMO-PKG-30', 10, 100, 1);
INSERT INTO bill_of_material VALUES
    ('DEMO-SKU-10', 'DEMO-API-01', 200, 127.5, 0),
    ('DEMO-SKU-10', 'DEMO-PKG-10', 200, 200, 0),
    ('DEMO-SKU-30', 'DEMO-API-01', 200, 382.5, 0),
    ('DEMO-SKU-30', 'DEMO-PKG-30', 200, 200, 0);
INSERT INTO sku_line VALUES ('DEMO-SKU-10', 'DEMO-LINE-01'), ('DEMO-SKU-30', 'DEMO-LINE-01');
INSERT INTO sku_market VALUES ('DEMO-SKU-10', 'DEMO-MKT-01', 50, 30), ('DEMO-SKU-30', 'DEMO-MKT-01', 20, 30);
INSERT INTO route VALUES
    ('DEMO-ROUTE-PD', 'DEMO-PLANT-01', 'DEMO-DC-01', 'ROAD', 0, 0),
    ('DEMO-ROUTE-DM', 'DEMO-DC-01', 'DEMO-MKT-01', 'ROAD', 2, 0);

INSERT INTO purchase_order (
    purchase_order_id, supplier_id, material_id, plant_id, ordered_on, planned_delivery_on,
    expected_delivery_on, actual_receipt_on, quantity_ordered, quantity_received, status, quality_status
) VALUES
    ('DEMO-PO-01', 'DEMO-SUP-API', 'DEMO-API-01', 'DEMO-PLANT-01',
     '2026-10-12', '2026-11-02', '2026-11-02', NULL, 150, 0, 'OPEN', 'PENDING'),
    ('DEMO-PO-PKG', 'DEMO-SUP-PKG', 'DEMO-PKG-10', 'DEMO-PLANT-01',
     '2026-10-12', '2026-10-26', '2026-10-26', '2026-10-26', 220, 220, 'RECEIVED', 'RELEASED');

INSERT INTO production_order (
    production_order_id, sku_id, line_id, plant_id, planned_start_on, planned_completion_on,
    actual_start_on, actual_completion_on, planned_quantity_packs, actual_quantity_packs,
    expected_yield_pct, actual_yield_pct, planned_hours, status
) VALUES
    ('DEMO-PROD-01', 'DEMO-SKU-10', 'DEMO-LINE-01', 'DEMO-PLANT-01',
     '2026-11-09', '2026-11-13', NULL, NULL, 200, NULL, 100, NULL, 32, 'PLANNED'),
    ('DEMO-PROD-HIST', 'DEMO-SKU-10', 'DEMO-LINE-01', 'DEMO-PLANT-01',
     '2026-10-12', '2026-10-16', '2026-10-12', '2026-10-16', 160, 160, 100, 100, 32, 'COMPLETED');

INSERT INTO material_requirement VALUES
    ('DEMO-REQ-API', 'DEMO-PROD-01', 'DEMO-SKU-10', 'DEMO-PLANT-01', 'DEMO-API-01', '2026-11-09', 127.5),
    ('DEMO-REQ-PKG', 'DEMO-PROD-01', 'DEMO-SKU-10', 'DEMO-PLANT-01', 'DEMO-PKG-10', '2026-11-09', 200);
INSERT INTO requirement_purchase_order VALUES
    ('DEMO-REQ-API', 'DEMO-PO-01', 'DEMO-API-01', 'DEMO-PLANT-01'),
    ('DEMO-REQ-PKG', 'DEMO-PO-PKG', 'DEMO-PKG-10', 'DEMO-PLANT-01');
INSERT INTO capacity (line_id, week_start, available_hours, maintenance_hours, downtime_hours, committed_hours) VALUES
    ('DEMO-LINE-01', '2026-11-09', 40, 0, 0, 32),
    ('DEMO-LINE-01', '2026-11-16', 40, 0, 0, 0);

INSERT INTO batch VALUES
    ('DEMO-BATCH-01', 'DEMO-PROD-01', 'DEMO-SKU-10', 'DEMO-PLANT-01',
     NULL, '2026-11-16', NULL, '2027-11-13', 200, 0, 'PENDING'),
    ('DEMO-BATCH-HIST', 'DEMO-PROD-HIST', 'DEMO-SKU-10', 'DEMO-PLANT-01',
     '2026-10-16', '2026-10-19', '2026-10-19', '2027-10-16', 160, 160, 'RELEASED');
INSERT INTO inventory_lot VALUES
    ('DEMO-LOT-API', 'DEMO-API-01', NULL, NULL, NULL, '2026-09-01', '2027-09-01'),
    ('DEMO-LOT-PKG', 'DEMO-PKG-10', 'DEMO-PO-PKG', NULL, NULL, '2026-10-01', '2028-03-24'),
    ('DEMO-LOT-FG', NULL, NULL, 'DEMO-BATCH-HIST', 'DEMO-SKU-10', '2026-10-16', '2027-10-16');
INSERT INTO inventory_snapshot (lot_id, location_id, snapshot_on, on_hand, reserved, blocked, in_transit) VALUES
    ('DEMO-LOT-API', 'DEMO-PLANT-01', '2026-11-01', 80, 0, 0, 0),
    ('DEMO-LOT-PKG', 'DEMO-PLANT-01', '2026-11-01', 220, 0, 0, 0),
    ('DEMO-LOT-FG', 'DEMO-MKT-01', '2026-11-01', 160, 0, 0, 0);

INSERT INTO shipment (
    shipment_id, route_id, origin_id, destination_id, batch_id, prior_shipment_id,
    planned_dispatch_on, expected_arrival_on, planned_quantity_packs
) VALUES
    ('DEMO-SHIP-DC', 'DEMO-ROUTE-PD', 'DEMO-PLANT-01', 'DEMO-DC-01', 'DEMO-BATCH-01',
     NULL, '2026-11-16', '2026-11-16', 200),
    ('DEMO-SHIP-MKT', 'DEMO-ROUTE-DM', 'DEMO-DC-01', 'DEMO-MKT-01', 'DEMO-BATCH-01',
     'DEMO-SHIP-DC', '2026-11-16', '2026-11-18', 200);

INSERT INTO demand_history (sku_id, market_id, week_start, demand_packs, fulfilled_packs, event_type) VALUES
    ('DEMO-SKU-10', 'DEMO-MKT-01', '2026-10-19', 100, 100, 'NONE'),
    ('DEMO-SKU-10', 'DEMO-MKT-01', '2026-10-26', 100, 100, 'NONE');
INSERT INTO forecast_version VALUES ('DEMO-FCST-01', '2026-11-01', '2026-10-31', 'HAND_ENTERED_FIXTURE', '1');
INSERT INTO demand_forecast VALUES
    ('DEMO-FCST-01', 'DEMO-SKU-10', 'DEMO-MKT-01', '2026-11-09', 100, 90, 110, NULL, NULL),
    ('DEMO-FCST-01', 'DEMO-SKU-10', 'DEMO-MKT-01', '2026-11-16', 100, 90, 110, NULL, NULL),
    ('DEMO-FCST-01', 'DEMO-SKU-10', 'DEMO-MKT-01', '2026-11-23', 100, 90, 110, NULL, NULL);

INSERT INTO scenario (scenario_id, name, kind) VALUES
    ('DEMO-BASE', 'Baseline plan', 'BASELINE'),
    ('DEMO-API-DELAY', 'API receipt delayed by 14 days', 'API_DELAY');
INSERT INTO api_receipt_delay (scenario_id, purchase_order_id, material_id, delay_days)
VALUES ('DEMO-API-DELAY', 'DEMO-PO-01', 'DEMO-API-01', 14);
