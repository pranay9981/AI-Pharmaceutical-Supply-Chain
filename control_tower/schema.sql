-- Dates are ISO 8601 calendar dates. Planning weeks start on Monday.
PRAGMA user_version = 1;

CREATE TABLE dataset (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    dataset_version TEXT NOT NULL,
    seed INTEGER,
    synthetic INTEGER NOT NULL DEFAULT 1 CHECK (synthetic = 1),
    disclaimer TEXT NOT NULL DEFAULT 'Synthetic data for demonstration only. Not for operational decision making.'
        CHECK (disclaimer = 'Synthetic data for demonstration only. Not for operational decision making.')
) STRICT;

CREATE TABLE product (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    therapy_area TEXT NOT NULL,
    dosage_form TEXT NOT NULL,
    lifecycle_stage TEXT NOT NULL,
    critical INTEGER NOT NULL CHECK (critical IN (0, 1))
) STRICT;

CREATE TABLE sku (
    sku_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES product,
    pack_size INTEGER NOT NULL CHECK (pack_size > 0),
    shelf_life_days INTEGER NOT NULL CHECK (shelf_life_days > 0),
    storage_condition TEXT NOT NULL CHECK (storage_condition IN ('AMBIENT', 'REFRIGERATED', 'FROZEN')),
    unit_cost_minor INTEGER NOT NULL CHECK (unit_cost_minor >= 0),
    currency TEXT NOT NULL CHECK (length(currency) = 3)
) STRICT;

CREATE TABLE location (
    location_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('PLANT', 'DC', 'MARKET')),
    region TEXT NOT NULL,
    storage_capacity_packs INTEGER NOT NULL CHECK (storage_capacity_packs >= 0),
    cold_chain_capable INTEGER NOT NULL CHECK (cold_chain_capable IN (0, 1)),
    UNIQUE (location_id, kind)
) STRICT;

CREATE TABLE market (
    market_id TEXT PRIMARY KEY,
    location_kind TEXT GENERATED ALWAYS AS ('MARKET') VIRTUAL,
    service_priority TEXT NOT NULL CHECK (service_priority IN ('STANDARD', 'HIGH')),
    FOREIGN KEY (market_id, location_kind) REFERENCES location (location_id, kind)
) STRICT;

CREATE TABLE production_line (
    line_id TEXT PRIMARY KEY,
    plant_id TEXT NOT NULL,
    location_kind TEXT GENERATED ALWAYS AS ('PLANT') VIRTUAL,
    name TEXT NOT NULL,
    UNIQUE (line_id, plant_id),
    FOREIGN KEY (plant_id, location_kind) REFERENCES location (location_id, kind)
) STRICT;

CREATE TABLE supplier (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    supplier_type TEXT NOT NULL,
    otif_target_pct REAL NOT NULL CHECK (otif_target_pct BETWEEN 0 AND 100),
    risk_tier TEXT NOT NULL CHECK (risk_tier IN ('LOW', 'MEDIUM', 'HIGH'))
) STRICT;

CREATE TABLE material (
    material_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('API', 'EXCIPIENT', 'PACKAGING')),
    unit TEXT NOT NULL CHECK (unit IN ('KG', 'EACH')),
    shelf_life_days INTEGER NOT NULL CHECK (shelf_life_days > 0),
    inspection_days INTEGER NOT NULL CHECK (inspection_days >= 0),
    critical INTEGER NOT NULL CHECK (critical IN (0, 1)),
    single_source INTEGER NOT NULL CHECK (single_source IN (0, 1)),
    UNIQUE (material_id, kind)
) STRICT;

CREATE TABLE supplier_material (
    supplier_id TEXT NOT NULL REFERENCES supplier,
    material_id TEXT NOT NULL REFERENCES material,
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
    minimum_order_quantity REAL NOT NULL CHECK (minimum_order_quantity > 0),
    is_primary INTEGER NOT NULL CHECK (is_primary IN (0, 1)),
    PRIMARY KEY (supplier_id, material_id)
) STRICT;

CREATE UNIQUE INDEX one_primary_supplier_per_material ON supplier_material (material_id) WHERE is_primary = 1;

CREATE TABLE bill_of_material (
    sku_id TEXT NOT NULL REFERENCES sku,
    material_id TEXT NOT NULL REFERENCES material,
    batch_size_packs INTEGER NOT NULL CHECK (batch_size_packs > 0),
    quantity_per_batch REAL NOT NULL CHECK (quantity_per_batch > 0),
    scrap_factor_pct REAL NOT NULL CHECK (scrap_factor_pct BETWEEN 0 AND 100),
    PRIMARY KEY (sku_id, material_id)
) STRICT;

CREATE TABLE sku_line (
    sku_id TEXT NOT NULL REFERENCES sku,
    line_id TEXT NOT NULL REFERENCES production_line,
    PRIMARY KEY (sku_id, line_id)
) STRICT;

CREATE TABLE sku_market (
    sku_id TEXT NOT NULL REFERENCES sku,
    market_id TEXT NOT NULL REFERENCES market,
    safety_stock_packs INTEGER NOT NULL CHECK (safety_stock_packs >= 0),
    minimum_remaining_shelf_life_days INTEGER NOT NULL CHECK (minimum_remaining_shelf_life_days >= 0),
    PRIMARY KEY (sku_id, market_id)
) STRICT;

CREATE TABLE route (
    route_id TEXT PRIMARY KEY,
    origin_id TEXT NOT NULL REFERENCES location,
    destination_id TEXT NOT NULL REFERENCES location,
    mode TEXT NOT NULL,
    transit_days INTEGER NOT NULL CHECK (transit_days >= 0),
    cold_chain_capable INTEGER NOT NULL CHECK (cold_chain_capable IN (0, 1)),
    UNIQUE (route_id, origin_id, destination_id),
    CHECK (origin_id <> destination_id)
) STRICT;

CREATE TABLE purchase_order (
    purchase_order_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    material_id TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    location_kind TEXT GENERATED ALWAYS AS ('PLANT') VIRTUAL,
    ordered_on TEXT NOT NULL CHECK (date(ordered_on, '+0 days') IS ordered_on),
    planned_delivery_on TEXT NOT NULL CHECK (date(planned_delivery_on, '+0 days') IS planned_delivery_on),
    expected_delivery_on TEXT NOT NULL CHECK (date(expected_delivery_on, '+0 days') IS expected_delivery_on),
    actual_receipt_on TEXT CHECK (date(actual_receipt_on, '+0 days') IS actual_receipt_on),
    quantity_ordered REAL NOT NULL CHECK (quantity_ordered > 0),
    quantity_received REAL NOT NULL DEFAULT 0 CHECK (quantity_received BETWEEN 0 AND quantity_ordered),
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'RECEIVED', 'CANCELLED')),
    quality_status TEXT NOT NULL CHECK (quality_status IN ('PENDING', 'RELEASED', 'BLOCKED')),
    delay_reason TEXT,
    UNIQUE (purchase_order_id, material_id),
    UNIQUE (purchase_order_id, material_id, plant_id),
    FOREIGN KEY (supplier_id, material_id) REFERENCES supplier_material,
    FOREIGN KEY (plant_id, location_kind) REFERENCES location (location_id, kind),
    CHECK (min(planned_delivery_on, expected_delivery_on) >= ordered_on),
    CHECK (actual_receipt_on IS NULL OR actual_receipt_on >= ordered_on),
    CHECK ((status = 'RECEIVED') = (actual_receipt_on IS NOT NULL)),
    CHECK ((actual_receipt_on IS NULL) = (quantity_received = 0)),
    CHECK (quality_status = 'PENDING' OR actual_receipt_on IS NOT NULL)
) STRICT;

CREATE TABLE production_order (
    production_order_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    line_id TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    planned_start_on TEXT NOT NULL CHECK (date(planned_start_on, '+0 days') IS planned_start_on),
    planned_completion_on TEXT NOT NULL CHECK (date(planned_completion_on, '+0 days') IS planned_completion_on),
    actual_start_on TEXT CHECK (date(actual_start_on, '+0 days') IS actual_start_on),
    actual_completion_on TEXT CHECK (date(actual_completion_on, '+0 days') IS actual_completion_on),
    planned_quantity_packs INTEGER NOT NULL CHECK (planned_quantity_packs > 0),
    actual_quantity_packs INTEGER CHECK (actual_quantity_packs >= 0),
    expected_yield_pct REAL NOT NULL CHECK (expected_yield_pct BETWEEN 0 AND 100),
    actual_yield_pct REAL CHECK (actual_yield_pct BETWEEN 0 AND 100),
    planned_hours REAL NOT NULL CHECK (planned_hours > 0),
    status TEXT NOT NULL CHECK (status IN ('PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    delay_reason TEXT,
    UNIQUE (production_order_id, sku_id, plant_id),
    FOREIGN KEY (sku_id, line_id) REFERENCES sku_line,
    FOREIGN KEY (line_id, plant_id) REFERENCES production_line (line_id, plant_id),
    CHECK (planned_completion_on >= planned_start_on),
    CHECK (actual_completion_on IS NULL OR (actual_start_on IS NOT NULL AND actual_completion_on >= actual_start_on)),
    CHECK (status <> 'COMPLETED' OR (actual_completion_on IS NOT NULL AND actual_quantity_packs IS NOT NULL))
) STRICT;

CREATE TABLE material_requirement (
    requirement_id TEXT PRIMARY KEY,
    production_order_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    material_id TEXT NOT NULL,
    need_on TEXT NOT NULL CHECK (date(need_on, '+0 days') IS need_on),
    required_quantity REAL NOT NULL CHECK (required_quantity > 0),
    UNIQUE (production_order_id, material_id),
    UNIQUE (requirement_id, material_id, plant_id),
    FOREIGN KEY (production_order_id, sku_id, plant_id) REFERENCES production_order (production_order_id, sku_id, plant_id),
    FOREIGN KEY (sku_id, material_id) REFERENCES bill_of_material
) STRICT;

CREATE TABLE requirement_purchase_order (
    requirement_id TEXT NOT NULL,
    purchase_order_id TEXT NOT NULL,
    material_id TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    PRIMARY KEY (requirement_id, purchase_order_id),
    FOREIGN KEY (requirement_id, material_id, plant_id) REFERENCES material_requirement (requirement_id, material_id, plant_id),
    FOREIGN KEY (purchase_order_id, material_id, plant_id) REFERENCES purchase_order (purchase_order_id, material_id, plant_id)
) STRICT;

CREATE TABLE capacity (
    line_id TEXT NOT NULL REFERENCES production_line,
    week_start TEXT NOT NULL CHECK (date(week_start, '+0 days', 'weekday 1') IS week_start),
    available_hours REAL NOT NULL CHECK (available_hours BETWEEN 0 AND 168),
    maintenance_hours REAL NOT NULL CHECK (maintenance_hours >= 0),
    downtime_hours REAL NOT NULL CHECK (downtime_hours >= 0),
    committed_hours REAL NOT NULL CHECK (committed_hours >= 0),
    net_available_hours REAL GENERATED ALWAYS AS (available_hours - maintenance_hours - downtime_hours) VIRTUAL,
    PRIMARY KEY (line_id, week_start),
    CHECK (net_available_hours >= 0)
) STRICT;

CREATE TABLE batch (
    batch_id TEXT PRIMARY KEY,
    production_order_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    manufactured_on TEXT CHECK (date(manufactured_on, '+0 days') IS manufactured_on),
    planned_release_on TEXT NOT NULL CHECK (date(planned_release_on, '+0 days') IS planned_release_on),
    actual_release_on TEXT CHECK (date(actual_release_on, '+0 days') IS actual_release_on),
    expiry_on TEXT NOT NULL CHECK (date(expiry_on, '+0 days') IS expiry_on),
    planned_quantity_packs INTEGER NOT NULL CHECK (planned_quantity_packs > 0),
    released_quantity_packs INTEGER NOT NULL DEFAULT 0 CHECK (released_quantity_packs >= 0),
    quality_status TEXT NOT NULL CHECK (quality_status IN ('PENDING', 'HELD', 'RELEASED', 'REJECTED')),
    UNIQUE (batch_id, sku_id),
    FOREIGN KEY (production_order_id, sku_id, plant_id) REFERENCES production_order (production_order_id, sku_id, plant_id),
    CHECK (manufactured_on IS NULL OR manufactured_on < expiry_on),
    CHECK (planned_release_on < expiry_on),
    CHECK (actual_release_on IS NULL OR (actual_release_on >= manufactured_on AND actual_release_on < expiry_on AND manufactured_on IS NOT NULL)),
    CHECK ((quality_status = 'RELEASED') = (actual_release_on IS NOT NULL)),
    CHECK ((quality_status = 'RELEASED') = (released_quantity_packs > 0))
) STRICT;

CREATE TABLE inventory_lot (
    lot_id TEXT PRIMARY KEY,
    material_id TEXT REFERENCES material,
    purchase_order_id TEXT,
    batch_id TEXT,
    sku_id TEXT,
    manufactured_on TEXT NOT NULL CHECK (date(manufactured_on, '+0 days') IS manufactured_on),
    expiry_on TEXT NOT NULL CHECK (date(expiry_on, '+0 days') IS expiry_on),
    FOREIGN KEY (purchase_order_id, material_id) REFERENCES purchase_order (purchase_order_id, material_id),
    FOREIGN KEY (batch_id, sku_id) REFERENCES batch (batch_id, sku_id),
    CHECK (
        (material_id IS NOT NULL AND batch_id IS NULL AND sku_id IS NULL) OR
        (material_id IS NULL AND purchase_order_id IS NULL AND batch_id IS NOT NULL AND sku_id IS NOT NULL)
    ),
    CHECK (expiry_on > manufactured_on)
) STRICT;

CREATE TABLE inventory_snapshot (
    lot_id TEXT NOT NULL REFERENCES inventory_lot,
    location_id TEXT NOT NULL REFERENCES location,
    snapshot_on TEXT NOT NULL CHECK (date(snapshot_on, '+0 days') IS snapshot_on),
    on_hand REAL NOT NULL CHECK (on_hand >= 0),
    reserved REAL NOT NULL CHECK (reserved >= 0),
    blocked REAL NOT NULL CHECK (blocked >= 0),
    in_transit REAL NOT NULL CHECK (in_transit >= 0),
    available REAL GENERATED ALWAYS AS (on_hand - reserved - blocked) VIRTUAL,
    PRIMARY KEY (lot_id, location_id, snapshot_on),
    CHECK (available >= 0)
) STRICT;

CREATE TABLE shipment (
    shipment_id TEXT PRIMARY KEY,
    route_id TEXT NOT NULL,
    origin_id TEXT NOT NULL,
    destination_id TEXT NOT NULL,
    batch_id TEXT NOT NULL REFERENCES batch,
    prior_shipment_id TEXT,
    planned_dispatch_on TEXT NOT NULL CHECK (date(planned_dispatch_on, '+0 days') IS planned_dispatch_on),
    expected_arrival_on TEXT NOT NULL CHECK (date(expected_arrival_on, '+0 days') IS expected_arrival_on),
    actual_dispatch_on TEXT CHECK (date(actual_dispatch_on, '+0 days') IS actual_dispatch_on),
    actual_arrival_on TEXT CHECK (date(actual_arrival_on, '+0 days') IS actual_arrival_on),
    planned_quantity_packs INTEGER NOT NULL CHECK (planned_quantity_packs > 0),
    shipped_quantity_packs INTEGER CHECK (shipped_quantity_packs > 0),
    received_quantity_packs INTEGER CHECK (received_quantity_packs BETWEEN 0 AND shipped_quantity_packs),
    customs_delay_days INTEGER NOT NULL DEFAULT 0 CHECK (customs_delay_days >= 0),
    temperature_excursion INTEGER NOT NULL DEFAULT 0 CHECK (temperature_excursion IN (0, 1)),
    UNIQUE (shipment_id, batch_id, destination_id),
    FOREIGN KEY (route_id, origin_id, destination_id) REFERENCES route (route_id, origin_id, destination_id),
    FOREIGN KEY (prior_shipment_id, batch_id, origin_id) REFERENCES shipment (shipment_id, batch_id, destination_id),
    CHECK (prior_shipment_id IS NULL OR prior_shipment_id <> shipment_id),
    CHECK (expected_arrival_on >= planned_dispatch_on),
    CHECK (actual_arrival_on IS NULL OR (actual_dispatch_on IS NOT NULL AND actual_arrival_on >= actual_dispatch_on)),
    CHECK ((shipped_quantity_packs IS NULL) = (actual_dispatch_on IS NULL)),
    CHECK ((received_quantity_packs IS NULL) = (actual_arrival_on IS NULL))
) STRICT;

CREATE TABLE demand_history (
    sku_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    week_start TEXT NOT NULL CHECK (date(week_start, '+0 days', 'weekday 1') IS week_start),
    demand_packs INTEGER NOT NULL CHECK (demand_packs >= 0),
    fulfilled_packs INTEGER NOT NULL CHECK (fulfilled_packs BETWEEN 0 AND demand_packs),
    lost_sales_packs INTEGER GENERATED ALWAYS AS (demand_packs - fulfilled_packs) VIRTUAL,
    event_type TEXT NOT NULL,
    drivers_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(drivers_json)),
    PRIMARY KEY (sku_id, market_id, week_start),
    FOREIGN KEY (sku_id, market_id) REFERENCES sku_market
) STRICT;

CREATE TABLE forecast_version (
    forecast_version_id TEXT PRIMARY KEY,
    issued_on TEXT NOT NULL CHECK (date(issued_on, '+0 days') IS issued_on),
    training_cutoff_on TEXT NOT NULL CHECK (date(training_cutoff_on, '+0 days') IS training_cutoff_on),
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    CHECK (training_cutoff_on <= issued_on)
) STRICT;

CREATE TABLE demand_forecast (
    forecast_version_id TEXT NOT NULL REFERENCES forecast_version,
    sku_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    week_start TEXT NOT NULL CHECK (date(week_start, '+0 days', 'weekday 1') IS week_start),
    forecast_packs REAL NOT NULL CHECK (forecast_packs >= 0),
    lower_packs REAL NOT NULL CHECK (lower_packs BETWEEN 0 AND forecast_packs),
    upper_packs REAL NOT NULL CHECK (upper_packs >= forecast_packs),
    override_packs REAL CHECK (override_packs >= 0),
    override_reason TEXT,
    PRIMARY KEY (forecast_version_id, sku_id, market_id, week_start),
    FOREIGN KEY (sku_id, market_id) REFERENCES sku_market,
    CHECK ((override_packs IS NULL) = (override_reason IS NULL))
) STRICT;

CREATE TABLE scenario (
    scenario_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('BASELINE', 'API_DELAY')),
    assumptions_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(assumptions_json)),
    UNIQUE (scenario_id, kind)
) STRICT;

CREATE TABLE api_receipt_delay (
    scenario_id TEXT PRIMARY KEY,
    scenario_kind TEXT GENERATED ALWAYS AS ('API_DELAY') VIRTUAL,
    purchase_order_id TEXT NOT NULL,
    material_id TEXT NOT NULL,
    material_kind TEXT GENERATED ALWAYS AS ('API') VIRTUAL,
    delay_days INTEGER NOT NULL CHECK (delay_days BETWEEN 0 AND 36500),
    FOREIGN KEY (scenario_id, scenario_kind) REFERENCES scenario (scenario_id, kind),
    FOREIGN KEY (purchase_order_id, material_id) REFERENCES purchase_order (purchase_order_id, material_id),
    FOREIGN KEY (material_id, material_kind) REFERENCES material (material_id, kind)
) STRICT;

CREATE TABLE planning_run (
    run_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL REFERENCES scenario,
    forecast_version_id TEXT NOT NULL REFERENCES forecast_version,
    as_of_on TEXT NOT NULL CHECK (date(as_of_on, '+0 days') IS as_of_on),
    parent_run_id TEXT REFERENCES planning_run,
    CHECK (parent_run_id IS NULL OR parent_run_id <> run_id)
) STRICT;

CREATE TABLE inventory_projection (
    projection_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES planning_run,
    sku_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    week_start TEXT NOT NULL CHECK (date(week_start, '+0 days', 'weekday 1') IS week_start),
    opening_packs REAL NOT NULL CHECK (opening_packs >= 0),
    receipt_packs REAL NOT NULL CHECK (receipt_packs >= 0),
    ineligible_packs REAL NOT NULL DEFAULT 0 CHECK (ineligible_packs BETWEEN 0 AND opening_packs + receipt_packs),
    demand_packs REAL NOT NULL CHECK (demand_packs >= 0),
    fulfilled_packs REAL NOT NULL CHECK (fulfilled_packs BETWEEN 0 AND demand_packs),
    safety_stock_packs INTEGER NOT NULL CHECK (safety_stock_packs >= 0),
    ending_packs REAL GENERATED ALWAYS AS (opening_packs + receipt_packs - ineligible_packs - fulfilled_packs) VIRTUAL,
    unserved_packs REAL GENERATED ALWAYS AS (demand_packs - fulfilled_packs) VIRTUAL,
    UNIQUE (run_id, sku_id, market_id, week_start),
    UNIQUE (projection_id, run_id),
    FOREIGN KEY (sku_id, market_id) REFERENCES sku_market,
    CHECK (ending_packs >= 0)
) STRICT;

CREATE TABLE risk_event (
    risk_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES planning_run,
    sku_id TEXT REFERENCES sku,
    market_id TEXT,
    risk_type TEXT NOT NULL CHECK (risk_type IN ('SUPPLIER_DELAY', 'SAFETY_STOCK', 'STOCKOUT', 'EXPIRY', 'DEMAND_ANOMALY')),
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'CLOSED')),
    severity TEXT NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    days_to_impact INTEGER NOT NULL CHECK (days_to_impact >= 0),
    shortage_packs REAL CHECK (shortage_packs >= 0),
    shortage_severity REAL NOT NULL CHECK (shortage_severity BETWEEN 0 AND 100),
    timing_severity REAL NOT NULL CHECK (timing_severity BETWEEN 0 AND 100),
    medicine_criticality REAL NOT NULL CHECK (medicine_criticality BETWEEN 0 AND 100),
    source_dependency REAL NOT NULL CHECK (source_dependency BETWEEN 0 AND 100),
    forecast_uncertainty REAL NOT NULL CHECK (forecast_uncertainty BETWEEN 0 AND 100),
    recovery_difficulty REAL NOT NULL CHECK (recovery_difficulty BETWEEN 0 AND 100),
    risk_score REAL GENERATED ALWAYS AS (
        (30 * shortage_severity + 20 * timing_severity + 15 * medicine_criticality +
         15 * source_dependency + 10 * forecast_uncertainty + 10 * recovery_difficulty) / 100.0
    ) VIRTUAL,
    UNIQUE (risk_id, run_id),
    FOREIGN KEY (sku_id, market_id) REFERENCES sku_market,
    CHECK (market_id IS NULL OR sku_id IS NOT NULL)
) STRICT;

CREATE TABLE risk_evidence (
    evidence_id TEXT PRIMARY KEY,
    risk_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('DRIVER', 'IMPACT', 'CONTEXT')),
    purchase_order_id TEXT REFERENCES purchase_order,
    requirement_id TEXT REFERENCES material_requirement,
    production_order_id TEXT REFERENCES production_order,
    batch_id TEXT REFERENCES batch,
    shipment_id TEXT REFERENCES shipment,
    lot_id TEXT REFERENCES inventory_lot,
    projection_id TEXT,
    forecast_version_id TEXT REFERENCES forecast_version,
    FOREIGN KEY (risk_id, run_id) REFERENCES risk_event (risk_id, run_id),
    FOREIGN KEY (projection_id, run_id) REFERENCES inventory_projection (projection_id, run_id),
    CHECK ((purchase_order_id IS NOT NULL) + (requirement_id IS NOT NULL) +
           (production_order_id IS NOT NULL) + (batch_id IS NOT NULL) + (shipment_id IS NOT NULL) +
           (lot_id IS NOT NULL) + (projection_id IS NOT NULL) + (forecast_version_id IS NOT NULL) = 1)
) STRICT;

CREATE TABLE recommendation (
    recommendation_id TEXT PRIMARY KEY,
    risk_id TEXT NOT NULL REFERENCES risk_event,
    simulated_run_id TEXT REFERENCES planning_run,
    action_type TEXT NOT NULL CHECK (action_type IN ('EXPEDITE', 'REALLOCATE', 'RESCHEDULE', 'MONITOR')),
    feasibility TEXT NOT NULL CHECK (feasibility IN ('FEASIBLE', 'INFEASIBLE', 'INSUFFICIENT_EVIDENCE')),
    cost_minor INTEGER CHECK (cost_minor >= 0),
    currency TEXT CHECK (length(currency) = 3),
    risk_reduction_points REAL CHECK (risk_reduction_points BETWEEN -100 AND 100),
    constraints_json TEXT NOT NULL CHECK (json_valid(constraints_json)),
    assumptions_json TEXT NOT NULL CHECK (json_valid(assumptions_json)),
    human_approval_required INTEGER NOT NULL DEFAULT 1 CHECK (human_approval_required = 1),
    CHECK ((cost_minor IS NULL) = (currency IS NULL))
) STRICT;

CREATE TABLE recommendation_review (
    review_id TEXT PRIMARY KEY,
    recommendation_id TEXT NOT NULL REFERENCES recommendation,
    reviewer_label TEXT NOT NULL CHECK (length(trim(reviewer_label)) > 0),
    reviewed_at TEXT NOT NULL CHECK (datetime(reviewed_at) IS NOT NULL),
    decision TEXT NOT NULL CHECK (decision IN ('APPROVED', 'REJECTED')),
    comment TEXT
) STRICT;

CREATE VIEW scenario_purchase_order AS
SELECT s.scenario_id, p.purchase_order_id, p.supplier_id, p.material_id, p.plant_id,
       p.planned_delivery_on, p.expected_delivery_on AS original_expected_delivery_on,
       CASE WHEN d.purchase_order_id IS NULL THEN 0 ELSE d.delay_days END AS delay_days,
       CASE WHEN d.purchase_order_id IS NULL THEN p.expected_delivery_on
            ELSE date(p.expected_delivery_on, printf('+%d days', d.delay_days)) END AS scenario_expected_delivery_on
FROM scenario AS s
CROSS JOIN purchase_order AS p
LEFT JOIN api_receipt_delay AS d
    ON d.scenario_id = s.scenario_id AND d.purchase_order_id = p.purchase_order_id;

CREATE VIEW market_supply_trace AS
SELECT m.market_id, b.sku_id, s.shipment_id, s.prior_shipment_id AS upstream_shipment_id,
       s.expected_arrival_on, b.batch_id, o.production_order_id, o.plant_id,
       r.requirement_id, r.material_id, r.need_on, p.purchase_order_id, p.supplier_id
FROM market AS m
JOIN shipment AS s ON s.destination_id = m.market_id
JOIN batch AS b ON b.batch_id = s.batch_id
JOIN production_order AS o ON o.production_order_id = b.production_order_id
JOIN material_requirement AS r ON r.production_order_id = o.production_order_id
LEFT JOIN requirement_purchase_order AS link ON link.requirement_id = r.requirement_id
LEFT JOIN purchase_order AS p ON p.purchase_order_id = link.purchase_order_id;
