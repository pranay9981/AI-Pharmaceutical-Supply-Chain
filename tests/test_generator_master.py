"""
Unit tests for Generator Architecture & Master Record Synthesizer.
Synthetic Data Generation Engine — Week 03, Day 10 Deliverable.

Verifies:
1. Seed reproducibility across generator calls.
2. Complete schema compliance of all 8 Master Dimension entities.
3. Complete schema compliance of all 4 Network Bridge entities.
4. BOM explosion, process scrap factors, and shared component linkage.
5. Sourcing parameters, lead times, and order multiples.
6. Market authorization, SLA targets, and MARSL shelf-life thresholds.
7. Logistics route connectivity, non-zero transit times, and self-loop prevention.
8. Scenario registry catalog baseline and benchmark injection coverage.
"""

import datetime
import pytest
from src.generator.config import GeneratorConfig
from src.generator.master_data import (
    generate_master_and_bridge_data,
    generate_products,
    generate_finished_skus,
    generate_materials,
    generate_suppliers,
    generate_locations,
    generate_customers,
    generate_markets,
    generate_production_lines,
    generate_bill_of_materials,
    generate_supplier_materials,
    generate_sku_markets,
    generate_location_routes,
    generate_scenarios,
    init_random_seed
)
from src.models.master import (
    DimProduct, DimFinishedSKU, DimMaterial, DimSupplier,
    DimLocation, DimCustomer, DimMarket, DimProductionLine
)
from src.models.bridges import (
    BridgeBillOfMaterial, BridgeSupplierMaterial, BridgeSKUMarket, BridgeLocationRoute
)
from src.models.control_tower import DimScenario


@pytest.fixture
def config():
    return GeneratorConfig(random_seed=20261014, synthetic_flag=True)


def test_seed_reproducibility(config):
    """Verifies that calling the master generator twice with the same seed produces identical data."""
    dataset_1 = generate_master_and_bridge_data(config)
    dataset_2 = generate_master_and_bridge_data(config)

    assert len(dataset_1) == len(dataset_2)
    for table_name in dataset_1:
        list_1 = dataset_1[table_name]
        list_2 = dataset_2[table_name]
        assert len(list_1) == len(list_2), f"Row count mismatch in table {table_name}"
        for obj_1, obj_2 in zip(list_1, list_2):
            assert obj_1.model_dump() == obj_2.model_dump(), f"Value divergence in table {table_name}"


def test_master_record_counts_and_validation(config):
    """Verifies row counts and Pydantic v2 validation for all 8 Master entities."""
    data = generate_master_and_bridge_data(config)

    # 1. dim_product (1 family: Augmentin)
    products = data["dim_product"]
    assert len(products) == 1
    assert isinstance(products[0], DimProduct)
    assert products[0].product_id == "PRD-AUG"
    assert products[0].critical_medicine_flag is True
    assert products[0].synthetic_data_flag is True

    # 2. dim_finished_sku (2 configurations: T10 strip & T30 bottle)
    skus = data["dim_finished_sku"]
    assert len(skus) == 2
    sku_ids = {s.finished_sku_id for s in skus}
    assert sku_ids == {"SKU-AUG-500-T10", "SKU-AUG-500-T30"}
    for s in skus:
        assert isinstance(s, DimFinishedSKU)
        assert s.shelf_life_days == 730
        assert s.status == "Active"

    # 3. dim_material (5 items: API, Excipient, Blister, Bottle, Carton)
    materials = data["dim_material"]
    assert len(materials) == 5
    mat_types = {m.material_type for m in materials}
    assert mat_types == {"API", "Excipient", "Blister Foil", "Bottle", "Carton"}
    api_mat = next(m for m in materials if m.material_sku_id == "MAT-API-001")
    assert api_mat.critical_material_flag is True
    assert api_mat.unit_of_measure == "kg"

    # 4. dim_supplier (2 vendors: API & Packaging)
    suppliers = data["dim_supplier"]
    assert len(suppliers) == 2
    sup_map = {s.supplier_id: s for s in suppliers}
    assert "SUP-001" in sup_map and "SUP-002" in sup_map
    assert sup_map["SUP-001"].single_source_dependency_flag is True
    assert sup_map["SUP-001"].otif_target == 95.0

    # 5. dim_location (6 facilities across Gujarat, Maharashtra, Telangana)
    locations = data["dim_location"]
    assert len(locations) == 6
    loc_types = {loc.location_type for loc in locations}
    assert "MANUFACTURING_PLANT" in loc_types
    assert "DISTRIBUTION_CENTRE" in loc_types
    assert "SUPPLIER" in loc_types
    assert "MARKET" in loc_types
    for loc in locations:
        assert isinstance(loc, DimLocation)
        assert loc.country == "India"
        assert loc.synthetic_entity_flag is True

    # 6. dim_market (2 commercial territories)
    markets = data["dim_market"]
    assert len(markets) == 2
    market_ids = {m.market_id for m in markets}
    assert market_ids == {"MKT-IN-HYD", "MKT-IN-PUN"}

    # 7. dim_customer (4 hospital/commercial accounts)
    customers = data["dim_customer"]
    assert len(customers) == 4
    for cust in customers:
        assert isinstance(cust, DimCustomer)
        assert cust.market_id in market_ids

    # 8. dim_production_line (2 plant lines)
    lines = data["dim_production_line"]
    assert len(lines) == 2
    for line in lines:
        assert isinstance(line, DimProductionLine)
        assert line.standard_rate > 0
        assert line.location_id == "LOC-PLANT-01"


def test_bridge_bom_structure_and_scrap_math(config):
    """Verifies BOM records, referential integrity, shared packaging, and scrap math."""
    boms = generate_bill_of_materials(config)
    assert len(boms) == 8

    t10_boms = [b for b in boms if b.finished_sku_id == "SKU-AUG-500-T10"]
    t30_boms = [b for b in boms if b.finished_sku_id == "SKU-AUG-500-T30"]
    assert len(t10_boms) == 4
    assert len(t30_boms) == 4

    # Verify shared component: MAT-PKG-CART used by both SKUs
    carton_boms = [b for b in boms if b.material_sku_id == "MAT-PKG-CART"]
    assert len(carton_boms) == 2
    carton_skus = {b.finished_sku_id for b in carton_boms}
    assert carton_skus == {"SKU-AUG-500-T10", "SKU-AUG-500-T30"}

    # Verify scrap calculation on T10 API (BOM-AUG-T10-01)
    # 0.00625 kg/pack + 2.0% scrap -> for 100,000 packs: 100000 * 0.00625 * 1.02 = 637.5 kg
    api_t10_bom = next(b for b in boms if b.bom_id == "BOM-AUG-T10-01")
    gross_req = api_t10_bom.calculate_gross_requirement(100000)
    assert gross_req == pytest.approx(637.5, rel=1e-5)


def test_bridge_supplier_material_parameters(config):
    """Verifies approved vendor catalog records and replenishment parameters."""
    sup_mats = generate_supplier_materials(config)
    assert len(sup_mats) == 5

    api_lane = next(sm for sm in sup_mats if sm.material_sku_id == "MAT-API-001")
    assert api_lane.supplier_id == "SUP-001"
    assert api_lane.supplier_lead_time_days == 21
    assert api_lane.minimum_order_quantity == 100.0
    assert api_lane.order_multiple == 50.0
    assert api_lane.approved_supplier_flag is True
    assert api_lane.supplier_priority == 1


def test_bridge_sku_market_marsl_thresholds(config):
    """Verifies market authorizations and differentiated MARSL thresholds."""
    sku_mkts = generate_sku_markets(config)
    assert len(sku_mkts) == 4

    hyd_t10 = next(sm for sm in sku_mkts if sm.finished_sku_id == "SKU-AUG-500-T10" and sm.market_id == "MKT-IN-HYD")
    pun_t10 = next(sm for sm in sku_mkts if sm.finished_sku_id == "SKU-AUG-500-T10" and sm.market_id == "MKT-IN-PUN")

    # Strict institutional hospital market requires 180 days MARSL
    assert hyd_t10.min_acceptable_rsl_days == 180
    assert hyd_t10.service_level_target == 98.0

    # Commercial retail market requires 90 days MARSL
    assert pun_t10.min_acceptable_rsl_days == 90
    assert pun_t10.service_level_target == 98.0


def test_bridge_location_routes_and_topology(config):
    """Verifies inter-facility transport corridors and endpoint validation."""
    routes = generate_location_routes(config)
    assert len(routes) == 3

    route_ids = {r.route_id for r in routes}
    assert route_ids == {"RT-PLANT1-DC01", "RT-DC01-MKTHYD", "RT-DC01-MKTPUN"}

    for r in routes:
        assert isinstance(r, BridgeLocationRoute)
        assert r.origin_location_id != r.destination_location_id
        assert r.standard_transit_days > 0
        assert r.transport_cost_per_unit > 0.0
        assert r.route_status == "Active"


def test_scenario_catalog_options(config):
    """Verifies baseline scenario catalog vs full benchmark suite generation."""
    # Baseline scope
    base_scenarios = generate_scenarios(config, include_all_benchmarks=False)
    assert len(base_scenarios) == 2
    base_ids = [s.scenario_id for s in base_scenarios]
    assert base_ids == ["SCN-BASE", "SCN-A-API-DELAY"]
    assert base_scenarios[0].baseline_flag is True
    assert base_scenarios[1].baseline_flag is False

    # Extended benchmark suite (Scenarios A through E)
    all_scenarios = generate_scenarios(config, include_all_benchmarks=True)
    assert len(all_scenarios) == 6
    all_ids = [s.scenario_id for s in all_scenarios]
    assert all_ids == [
        "SCN-BASE",
        "SCN-A-API-DELAY",
        "SCN-B-BATCH-HOLD",
        "SCN-C-CARTON-SHORTAGE",
        "SCN-D-FEFO-EXPOSURE",
        "SCN-E-CAPACITY-CONFLICT"
    ]
