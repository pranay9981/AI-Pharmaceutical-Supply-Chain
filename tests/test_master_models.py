"""
Pytest Unit Test Suite for Master Data Entities (8 Tables).
Technical Verification for Week 02, Day 05 Deliverable.

Tests instantiation, field constraints, range validations, enum behaviors,
and error handling across all 8 master data entities.
"""

from datetime import date
import pytest
from pydantic import ValidationError
from src.models.master import (
    DimProduct,
    DimFinishedSKU,
    DimMaterial,
    DimSupplier,
    DimLocation,
    DimCustomer,
    DimMarket,
    DimProductionLine,
)


def test_dim_product_instantiation_and_validation():
    # Valid product
    p = DimProduct(
        product_id="PRD-AUG",
        product_name="Augmentin",
        product_family="Antibiotic-Penicillin",
        therapy_area="Anti-Infectives",
        critical_medicine_flag=True
    )
    assert p.product_id == "PRD-AUG"
    assert p.critical_medicine_flag is True
    assert p.synthetic_data_flag is True

    # Empty product_id should fail
    with pytest.raises(ValidationError):
        DimProduct(
            product_id="   ",
            product_name="Augmentin",
            product_family="Antibiotic-Penicillin",
            therapy_area="Anti-Infectives"
        )


def test_dim_finished_sku_validation():
    # Valid finished SKU
    sku = DimFinishedSKU(
        finished_sku_id="SKU-AUG-500-T10",
        product_id="PRD-AUG",
        sku_description="Augmentin 500mg/125mg Tablet (Strip Pack of 10)",
        dosage_form="Tablet",
        strength="500mg/125mg",
        pack_configuration="10-Tablet Alu-Alu Strip",
        shelf_life_days=730,
        storage_condition="Ambient",
        launch_date=date(2023, 1, 15)
    )
    assert sku.finished_sku_id == "SKU-AUG-500-T10"
    assert sku.shelf_life_days == 730

    # Negative shelf life should raise ValidationError
    with pytest.raises(ValidationError):
        DimFinishedSKU(
            finished_sku_id="SKU-AUG-500-T10",
            product_id="PRD-AUG",
            sku_description="Augmentin 500mg/125mg Tablet",
            dosage_form="Tablet",
            strength="500mg/125mg",
            pack_configuration="10-Tablet Alu-Alu Strip",
            shelf_life_days=-10,
            launch_date=date(2023, 1, 15)
        )


def test_dim_material_validation():
    # Valid Material
    mat = DimMaterial(
        material_sku_id="MAT-API-001",
        material_name="Synthetic Amoxicillin / Clavulanate API Blend",
        material_type="API",
        unit_of_measure="kg",
        shelf_life_days=540,
        retest_interval_days=365,
        release_time_days=5,
        critical_material_flag=True
    )
    assert mat.material_sku_id == "MAT-API-001"
    assert mat.release_time_days == 5

    # Negative release time days should fail
    with pytest.raises(ValidationError):
        DimMaterial(
            material_sku_id="MAT-API-001",
            material_name="API Blend",
            material_type="API",
            unit_of_measure="kg",
            shelf_life_days=540,
            release_time_days=-2
        )


def test_dim_supplier_validation_and_otif_bounds():
    # Valid Supplier
    sup = DimSupplier(
        supplier_id="SUP-001",
        supplier_name="Deccan Active Pharma Chem Pvt Ltd",
        supplier_type="API Manufacturer",
        default_lead_time_days=21,
        minimum_order_quantity=100.0,
        order_multiple=50.0,
        otif_target=95.0,
        risk_tier="Medium",
        single_source_dependency_flag=True
    )
    assert sup.supplier_id == "SUP-001"
    assert sup.otif_target == 95.0

    # OTIF target > 100% should fail
    with pytest.raises(ValidationError):
        DimSupplier(
            supplier_id="SUP-001",
            supplier_name="Deccan Chem",
            supplier_type="API Manufacturer",
            default_lead_time_days=21,
            otif_target=105.0
        )

    # Negative OTIF target should fail
    with pytest.raises(ValidationError):
        DimSupplier(
            supplier_id="SUP-001",
            supplier_name="Deccan Chem",
            supplier_type="API Manufacturer",
            default_lead_time_days=21,
            otif_target=-5.0
        )


def test_dim_location_validation():
    # Valid Location
    loc = DimLocation(
        location_id="LOC-PLANT-01",
        location_name="Plant Alpha Hyderabad Pharma Campus",
        location_type="MANUFACTURING_PLANT",
        city="Hyderabad",
        state="Telangana",
        country="India",
        capacity=60000.0,
        cold_chain_capable=False
    )
    assert loc.location_id == "LOC-PLANT-01"
    assert loc.country == "India"
    assert loc.capacity == 60000.0


def test_dim_customer_validation():
    # Valid Customer
    cust = DimCustomer(
        customer_id="CUST-001",
        customer_name="Telangana State Health Wholesalers Ltd",
        market_id="MKT-IN-HYD",
        customer_type="Wholesaler",
        service_priority="Tier-1"
    )
    assert cust.customer_id == "CUST-001"
    assert cust.service_priority == "Tier-1"


def test_dim_market_validation():
    # Valid Market
    mkt = DimMarket(
        market_id="MKT-IN-HYD",
        market_name="Hyderabad Metro & Telangana Zone",
        city="Hyderabad",
        state="Telangana",
        region="South"
    )
    assert mkt.market_id == "MKT-IN-HYD"
    assert mkt.region == "South"


def test_dim_production_line_validation_and_rate():
    # Valid Production Line
    line = DimProductionLine(
        production_line_id="LINE-PLANT1-01",
        location_id="LOC-PLANT-01",
        line_name="Oral Solid Dosage Granulation & Compression Line 1",
        capacity_unit="hours_per_week",
        standard_rate=5000.0,
        supported_product_group="Solid Oral Antibiotics"
    )
    assert line.production_line_id == "LINE-PLANT1-01"
    assert line.standard_rate == 5000.0

    # Non-positive standard rate should fail
    with pytest.raises(ValidationError):
        DimProductionLine(
            production_line_id="LINE-PLANT1-01",
            location_id="LOC-PLANT-01",
            line_name="Line 1",
            standard_rate=0.0,
            supported_product_group="Solid Oral Antibiotics"
        )

