"""
Pytest Unit Test Suite for Network Topology & Bridge Entities (4 Tables).
Technical Verification for Week 02, Day 06 Deliverable.

Tests instantiation, field constraints, scrap factor calculations, date validations,
and error handling across all 4 bridge tables:
- BridgeBillOfMaterial
- BridgeSupplierMaterial
- BridgeSKUMarket
- BridgeLocationRoute
"""

from datetime import date
import pytest
from pydantic import ValidationError
from src.models.bridges import (
    BridgeBillOfMaterial,
    BridgeSupplierMaterial,
    BridgeSKUMarket,
    BridgeLocationRoute,
    TransportMode,
    RouteStatus,
)


def test_bridge_bom_instantiation_and_gross_calculation():
    # Valid BOM record: 1 pack of T10 requires 0.00625 kg API with 2.0% scrap
    bom = BridgeBillOfMaterial(
        bom_id="BOM-AUG-T10-01",
        finished_sku_id="SKU-AUG-500-T10",
        material_sku_id="MAT-API-001",
        quantity_per_finished_unit=0.00625,
        scrap_factor_pct=2.0,
        effective_start_date=date(2023, 1, 1),
        bom_version="V1"
    )
    assert bom.bom_id == "BOM-AUG-T10-01"
    assert bom.quantity_per_finished_unit == 0.00625
    assert bom.scrap_factor_pct == 2.0

    # Test gross requirement calculation:
    # 10,000 packs * 0.00625 kg = 62.5 kg net.
    # With 2% scrap: 62.5 * 1.02 = 63.75 kg gross.
    gross = bom.calculate_gross_requirement(10000.0)
    assert pytest.approx(gross, rel=1e-5) == 63.75


def test_bridge_bom_date_validation_and_scrap_bounds():
    # Invalid dates: effective_end_date earlier than effective_start_date
    with pytest.raises(ValidationError):
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-01",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-API-001",
            quantity_per_finished_unit=0.00625,
            scrap_factor_pct=2.0,
            effective_start_date=date(2025, 1, 1),
            effective_end_date=date(2024, 1, 1)  # Invalid!
        )

    # Invalid scrap factor (> 50%)
    with pytest.raises(ValidationError):
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-01",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-API-001",
            quantity_per_finished_unit=0.00625,
            scrap_factor_pct=60.0,  # Exceeds max 50%
            effective_start_date=date(2023, 1, 1)
        )


def test_bridge_supplier_material_validation():
    # Valid vendor-material pairing
    sm = BridgeSupplierMaterial(
        supplier_id="SUP-001",
        material_sku_id="MAT-API-001",
        supplier_lead_time_days=21,
        minimum_order_quantity=100.0,
        order_multiple=50.0,
        approved_supplier_flag=True,
        supplier_priority=1,
        effective_start_date=date(2023, 1, 1)
    )
    assert sm.supplier_id == "SUP-001"
    assert sm.supplier_lead_time_days == 21
    assert sm.approved_supplier_flag is True

    # Non-positive lead time should fail
    with pytest.raises(ValidationError):
        BridgeSupplierMaterial(
            supplier_id="SUP-001",
            material_sku_id="MAT-API-001",
            supplier_lead_time_days=0,  # Invalid!
            effective_start_date=date(2023, 1, 1)
        )


def test_bridge_sku_market_marsl_and_service_target():
    # Valid SKU-Market pairing with 90-day MARSL rule
    smkt = BridgeSKUMarket(
        finished_sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        market_priority=1,
        service_level_target=98.0,
        min_acceptable_rsl_days=90,
        effective_start_date=date(2023, 1, 15)
    )
    assert smkt.finished_sku_id == "SKU-AUG-500-T10"
    assert smkt.min_acceptable_rsl_days == 90
    assert smkt.service_level_target == 98.0

    # Invalid service level (> 100%)
    with pytest.raises(ValidationError):
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T10",
            market_id="MKT-IN-HYD",
            service_level_target=105.0,  # Invalid!
            effective_start_date=date(2023, 1, 15)
        )


def test_bridge_location_route_validation():
    # Valid route from Plant Pune to Central DC Nagpur
    route = BridgeLocationRoute(
        route_id="RT-PLANT1-DC01",
        origin_location_id="LOC-PLANT-01",
        destination_location_id="LOC-DC-01",
        transport_mode=TransportMode.ROAD,
        standard_transit_days=2,
        transport_cost_per_unit=0.35,
        cold_chain_required_flag=False,
        route_status=RouteStatus.ACTIVE
    )
    assert route.route_id == "RT-PLANT1-DC01"
    assert route.standard_transit_days == 2
    assert route.transport_mode == "Road"

    # Same origin and destination should fail
    with pytest.raises(ValidationError):
        BridgeLocationRoute(
            route_id="RT-LOOP-01",
            origin_location_id="LOC-PLANT-01",
            destination_location_id="LOC-PLANT-01",  # Same node invalid!
            standard_transit_days=1
        )

