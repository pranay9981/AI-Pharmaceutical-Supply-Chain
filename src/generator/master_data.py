"""
Master Data & Network Bridge Synthesizer.
Synthetic Data Generation Engine — Week 03, Day 10 Deliverable.

Generates validated Pydantic v2 master dimension records and network bridge tables
modeling an Indian pharmaceutical multi-echelon supply network for Augmentin 625mg.
Enforces deterministic reproducibility via a fixed random seed (default: 20261014).
"""

import datetime
import random
from typing import Dict, List, Optional
import numpy as np

from src.generator.config import GeneratorConfig
from src.models.master import (
    DimProduct,
    DimFinishedSKU,
    DimMaterial,
    DimSupplier,
    DimLocation,
    DimCustomer,
    DimMarket,
    DimProductionLine,
    LocationType,
    SupplierRiskTier,
    CustomerType,
    ServicePriority,
    StorageCondition
)
from src.models.bridges import (
    BridgeBillOfMaterial,
    BridgeSupplierMaterial,
    BridgeSKUMarket,
    BridgeLocationRoute,
    TransportMode,
    RouteStatus
)
from src.models.control_tower import DimScenario


def init_random_seed(seed: int = 20261014) -> None:
    """Sets deterministic random seed across Python random and NumPy."""
    random.seed(seed)
    np.random.seed(seed)


def generate_products(config: GeneratorConfig) -> List[DimProduct]:
    """Generates DimProduct master entities."""
    return [
        DimProduct(
            product_id="PRD-AUG",
            product_name="Augmentin",
            product_family="Antibiotic-Penicillin",
            therapy_area="Anti-Infectives",
            critical_medicine_flag=True,
            synthetic_data_flag=config.synthetic_flag
        )
    ]


def generate_finished_skus(config: GeneratorConfig) -> List[DimFinishedSKU]:
    """
    Generates DimFinishedSKU master entities.
    Two presentations: 10-tablet blister strip and 30-tablet HDPE bottle.
    """
    return [
        DimFinishedSKU(
            finished_sku_id="SKU-AUG-500-T10",
            product_id="PRD-AUG",
            sku_description="Augmentin 500mg/125mg Tablet (Strip Pack of 10)",
            dosage_form="Tablet",
            strength="500mg/125mg",
            pack_configuration="10-Tablet Alu-Alu Strip",
            shelf_life_days=730,  # 2 years
            storage_condition="Ambient",
            launch_date=datetime.date(2023, 1, 15),
            status="Active",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimFinishedSKU(
            finished_sku_id="SKU-AUG-500-T30",
            product_id="PRD-AUG",
            sku_description="Augmentin 500mg/125mg Tablet (Bottle Pack of 30)",
            dosage_form="Tablet",
            strength="500mg/125mg",
            pack_configuration="30-Tablet HDPE Bottle",
            shelf_life_days=730,  # 2 years
            storage_condition="Ambient",
            launch_date=datetime.date(2023, 6, 1),
            status="Active",
            synthetic_data_flag=config.synthetic_flag
        )
    ]


def generate_materials(config: GeneratorConfig) -> List[DimMaterial]:
    """
    Generates DimMaterial raw materials and packaging components.
    Includes active pharmaceutical ingredients (APIs), excipients, and primary/secondary packaging.
    """
    return [
        DimMaterial(
            material_sku_id="MAT-API-001",
            material_name="Synthetic Amoxicillin / Clavulanate API Blend",
            material_type="API",
            unit_of_measure="kg",
            shelf_life_days=540,  # 18 months
            retest_interval_days=365,
            release_time_days=5,
            critical_material_flag=True,
            storage_condition="Ambient",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimMaterial(
            material_sku_id="MAT-EXC-001",
            material_name="Microcrystalline Cellulose & Excipient Granules",
            material_type="Excipient",
            unit_of_measure="kg",
            shelf_life_days=720,  # 24 months
            retest_interval_days=365,
            release_time_days=3,
            critical_material_flag=False,
            storage_condition="Ambient",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimMaterial(
            material_sku_id="MAT-PKG-BLIST",
            material_name="Printed Aluminum Blister Foil Strip (T10)",
            material_type="Blister Foil",
            unit_of_measure="units",
            shelf_life_days=1095,  # 36 months
            retest_interval_days=None,
            release_time_days=2,
            critical_material_flag=False,
            storage_condition="Ambient",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimMaterial(
            material_sku_id="MAT-PKG-BOTT",
            material_name="HDPE Pharmaceutical Bottle & Closure 100cc (T30)",
            material_type="Bottle",
            unit_of_measure="units",
            shelf_life_days=1095,  # 36 months
            retest_interval_days=None,
            release_time_days=2,
            critical_material_flag=False,
            storage_condition="Ambient",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimMaterial(
            material_sku_id="MAT-PKG-CART",
            material_name="Printed Outer Carton Packaging Box",
            material_type="Carton",
            unit_of_measure="units",
            shelf_life_days=730,  # 24 months
            retest_interval_days=None,
            release_time_days=2,
            critical_material_flag=True,
            storage_condition="Ambient",
            synthetic_data_flag=config.synthetic_flag
        )
    ]


def generate_suppliers(config: GeneratorConfig) -> List[DimSupplier]:
    """
    Generates DimSupplier qualified chemical and packaging vendors.
    """
    return [
        DimSupplier(
            supplier_id="SUP-001",
            supplier_name="Deccan Active Pharma Chem Pvt Ltd",
            supplier_type="API Manufacturer",
            default_lead_time_days=21,
            minimum_order_quantity=100.0,
            order_multiple=50.0,
            otif_target=95.0,
            risk_tier="Medium",
            single_source_dependency_flag=True,
            synthetic_data_flag=config.synthetic_flag
        ),
        DimSupplier(
            supplier_id="SUP-002",
            supplier_name="Western Healthcare Packaging Solutions Ltd",
            supplier_type="Packaging Supplier",
            default_lead_time_days=14,
            minimum_order_quantity=5000.0,
            order_multiple=1000.0,
            otif_target=96.0,
            risk_tier="Low",
            single_source_dependency_flag=False,
            synthetic_data_flag=config.synthetic_flag
        )
    ]


def generate_locations(config: GeneratorConfig) -> List[DimLocation]:
    """
    Generates DimLocation network topology nodes across Indian geography:
    - Gujarat: API chemical synthesis
    - Maharashtra: Packaging conversion & central distribution (Nagpur, Pune)
    - Telangana: Manufacturing formulation & regional commercial hub (Hyderabad)
    """
    return [
        DimLocation(
            location_id="LOC-SUP-01",
            location_name="Deccan API Synthesis Plant",
            location_type="SUPPLIER",
            city="Ahmedabad",
            state="Gujarat",
            country="India",
            capacity=100000.0,
            cold_chain_capable=False,
            synthetic_entity_flag=config.synthetic_flag
        ),
        DimLocation(
            location_id="LOC-SUP-02",
            location_name="Western Packaging Converting Facility",
            location_type="SUPPLIER",
            city="Pune",
            state="Maharashtra",
            country="India",
            capacity=500000.0,
            cold_chain_capable=False,
            synthetic_entity_flag=config.synthetic_flag
        ),
        DimLocation(
            location_id="LOC-PLANT-01",
            location_name="Plant Alpha Hyderabad Pharma Campus",
            location_type="MANUFACTURING_PLANT",
            city="Hyderabad",
            state="Telangana",
            country="India",
            capacity=60000.0,  # packs per week
            cold_chain_capable=False,
            synthetic_entity_flag=config.synthetic_flag
        ),
        DimLocation(
            location_id="LOC-DC-01",
            location_name="Central India Logistics Distribution Centre",
            location_type="DISTRIBUTION_CENTRE",
            city="Nagpur",
            state="Maharashtra",
            country="India",
            capacity=250000.0,  # warehouse capacity packs
            cold_chain_capable=False,
            synthetic_entity_flag=config.synthetic_flag
        ),
        DimLocation(
            location_id="LOC-MKT-HYD",
            location_name="Hyderabad Metro Regional Hub",
            location_type="MARKET",
            city="Hyderabad",
            state="Telangana",
            country="India",
            capacity=0.0,
            cold_chain_capable=False,
            synthetic_entity_flag=config.synthetic_flag
        ),
        DimLocation(
            location_id="LOC-MKT-PUN",
            location_name="Pune Urban Regional Hub",
            location_type="MARKET",
            city="Pune",
            state="Maharashtra",
            country="India",
            capacity=0.0,
            cold_chain_capable=False,
            synthetic_entity_flag=config.synthetic_flag
        )
    ]


def generate_markets(config: GeneratorConfig) -> List[DimMarket]:
    """Generates DimMarket commercial demand zones."""
    return [
        DimMarket(
            market_id="MKT-IN-HYD",
            market_name="Hyderabad Metro & Telangana Zone",
            city="Hyderabad",
            state="Telangana",
            region="South",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimMarket(
            market_id="MKT-IN-PUN",
            market_name="Pune Urban & Western Maharashtra Zone",
            city="Pune",
            state="Maharashtra",
            region="West",
            synthetic_data_flag=config.synthetic_flag
        )
    ]


def generate_customers(config: GeneratorConfig) -> List[DimCustomer]:
    """Generates DimCustomer hospital networks, wholesalers, and pharmacy chains."""
    return [
        DimCustomer(
            customer_id="CUST-001",
            customer_name="Telangana State Health Wholesalers Ltd",
            market_id="MKT-IN-HYD",
            customer_type="Wholesaler",
            service_priority="Tier-1",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimCustomer(
            customer_id="CUST-002",
            customer_name="Deccan Apex Hospital Network",
            market_id="MKT-IN-HYD",
            customer_type="Hospital",
            service_priority="Tier-1",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimCustomer(
            customer_id="CUST-003",
            customer_name="Western Medical Logistics Consortium",
            market_id="MKT-IN-PUN",
            customer_type="Wholesaler",
            service_priority="Tier-1",
            synthetic_data_flag=config.synthetic_flag
        ),
        DimCustomer(
            customer_id="CUST-004",
            customer_name="Sahyadri Care Clinics & Pharmacies",
            market_id="MKT-IN-PUN",
            customer_type="Pharmacy Chain",
            service_priority="Tier-2",
            synthetic_data_flag=config.synthetic_flag
        )
    ]


def generate_production_lines(config: GeneratorConfig) -> List[DimProductionLine]:
    """Generates DimProductionLine formulation and packaging machinery."""
    return [
        DimProductionLine(
            production_line_id="LINE-PLANT1-01",
            location_id="LOC-PLANT-01",
            line_name="Oral Solid Dosage Granulation & Compression Line 1",
            capacity_unit="hours_per_week",
            standard_rate=5000.0,  # packs equivalent per hour
            supported_product_group="Solid Oral Antibiotics",
            maintenance_constraints="4 hours routine weekly CIP and tooling inspection on Sunday"
        ),
        DimProductionLine(
            production_line_id="LINE-PLANT1-02",
            location_id="LOC-PLANT-01",
            line_name="High-Speed Blister Thermoforming & Cartoning Line 2",
            capacity_unit="hours_per_week",
            standard_rate=6000.0,
            supported_product_group="Solid Oral Antibiotics",
            maintenance_constraints="4 hours line changeover and visual inspection check on Sunday"
        )
    ]


def generate_bill_of_materials(config: GeneratorConfig) -> List[BridgeBillOfMaterial]:
    """
    Generates BridgeBillOfMaterial formulation records.
    - 1 pack of T10 (10 tablets) requires:
      - 0.00625 kg API (6.25g) + 2.0% scrap
      - 0.00200 kg Excipient (2.0g) + 1.5% scrap
      - 1 Blister foil strip + 1.0% scrap
      - 1 Outer carton + 1.0% scrap
    - 1 pack of T30 (30 tablets) requires:
      - 0.01875 kg API (18.75g) + 2.0% scrap
      - 0.00600 kg Excipient (6.0g) + 1.5% scrap
      - 1 HDPE bottle + 1.0% scrap
      - 1 Outer carton (shared component!) + 1.0% scrap
    """
    return [
        # SKU-AUG-500-T10
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-01",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-API-001",
            quantity_per_finished_unit=0.00625,
            scrap_factor_pct=2.0,
            effective_start_date=datetime.date(2023, 1, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-02",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-EXC-001",
            quantity_per_finished_unit=0.00200,
            scrap_factor_pct=1.5,
            effective_start_date=datetime.date(2023, 1, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-03",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-PKG-BLIST",
            quantity_per_finished_unit=1.0,
            scrap_factor_pct=1.0,
            effective_start_date=datetime.date(2023, 1, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-04",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-PKG-CART",
            quantity_per_finished_unit=1.0,
            scrap_factor_pct=1.0,
            effective_start_date=datetime.date(2023, 1, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        # SKU-AUG-500-T30
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T30-01",
            finished_sku_id="SKU-AUG-500-T30",
            material_sku_id="MAT-API-001",
            quantity_per_finished_unit=0.01875,
            scrap_factor_pct=2.0,
            effective_start_date=datetime.date(2023, 6, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T30-02",
            finished_sku_id="SKU-AUG-500-T30",
            material_sku_id="MAT-EXC-001",
            quantity_per_finished_unit=0.00600,
            scrap_factor_pct=1.5,
            effective_start_date=datetime.date(2023, 6, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T30-03",
            finished_sku_id="SKU-AUG-500-T30",
            material_sku_id="MAT-PKG-BOTT",
            quantity_per_finished_unit=1.0,
            scrap_factor_pct=1.0,
            effective_start_date=datetime.date(2023, 6, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T30-04",
            finished_sku_id="SKU-AUG-500-T30",
            material_sku_id="MAT-PKG-CART",
            quantity_per_finished_unit=1.0,
            scrap_factor_pct=1.0,
            effective_start_date=datetime.date(2023, 6, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        )
    ]


def generate_supplier_materials(config: GeneratorConfig) -> List[BridgeSupplierMaterial]:
    """Generates BridgeSupplierMaterial approved vendor catalog records."""
    return [
        BridgeSupplierMaterial(
            supplier_id="SUP-001",
            material_sku_id="MAT-API-001",
            supplier_lead_time_days=21,
            minimum_order_quantity=100.0,
            order_multiple=50.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        ),
        BridgeSupplierMaterial(
            supplier_id="SUP-001",
            material_sku_id="MAT-EXC-001",
            supplier_lead_time_days=14,
            minimum_order_quantity=200.0,
            order_multiple=50.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        ),
        BridgeSupplierMaterial(
            supplier_id="SUP-002",
            material_sku_id="MAT-PKG-BLIST",
            supplier_lead_time_days=14,
            minimum_order_quantity=5000.0,
            order_multiple=1000.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        ),
        BridgeSupplierMaterial(
            supplier_id="SUP-002",
            material_sku_id="MAT-PKG-BOTT",
            supplier_lead_time_days=14,
            minimum_order_quantity=5000.0,
            order_multiple=1000.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        ),
        BridgeSupplierMaterial(
            supplier_id="SUP-002",
            material_sku_id="MAT-PKG-CART",
            supplier_lead_time_days=14,
            minimum_order_quantity=5000.0,
            order_multiple=1000.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        )
    ]


def generate_sku_markets(config: GeneratorConfig) -> List[BridgeSKUMarket]:
    """
    Generates BridgeSKUMarket market authorization and MARSL constraints.
    - Hyderabad Metro: Institutional hospital tender market with strict MARSL = 180 days.
    - Pune Urban: Commercial retail distribution with standard MARSL = 90 days.
    """
    return [
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T10",
            market_id="MKT-IN-HYD",
            market_priority=1,
            service_level_target=98.0,
            min_acceptable_rsl_days=180,
            effective_start_date=datetime.date(2023, 1, 15)
        ),
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T10",
            market_id="MKT-IN-PUN",
            market_priority=1,
            service_level_target=98.0,
            min_acceptable_rsl_days=90,
            effective_start_date=datetime.date(2023, 1, 15)
        ),
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T30",
            market_id="MKT-IN-HYD",
            market_priority=1,
            service_level_target=95.0,
            min_acceptable_rsl_days=180,
            effective_start_date=datetime.date(2023, 6, 1)
        ),
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T30",
            market_id="MKT-IN-PUN",
            market_priority=1,
            service_level_target=95.0,
            min_acceptable_rsl_days=90,
            effective_start_date=datetime.date(2023, 6, 1)
        )
    ]


def generate_location_routes(config: GeneratorConfig) -> List[BridgeLocationRoute]:
    """Generates BridgeLocationRoute physical logistics transport corridors."""
    return [
        # Plant Alpha Hyderabad -> Central DC Nagpur
        BridgeLocationRoute(
            route_id="RT-PLANT1-DC01",
            origin_location_id="LOC-PLANT-01",
            destination_location_id="LOC-DC-01",
            transport_mode="Road",
            standard_transit_days=2,
            transport_cost_per_unit=0.35,
            cold_chain_required_flag=False,
            route_status="Active"
        ),
        # Central DC Nagpur -> Market Hub Hyderabad
        BridgeLocationRoute(
            route_id="RT-DC01-MKTHYD",
            origin_location_id="LOC-DC-01",
            destination_location_id="LOC-MKT-HYD",
            transport_mode="Road",
            standard_transit_days=1,
            transport_cost_per_unit=0.20,
            cold_chain_required_flag=False,
            route_status="Active"
        ),
        # Central DC Nagpur -> Market Hub Pune
        BridgeLocationRoute(
            route_id="RT-DC01-MKTPUN",
            origin_location_id="LOC-DC-01",
            destination_location_id="LOC-MKT-PUN",
            transport_mode="Road",
            standard_transit_days=2,
            transport_cost_per_unit=0.25,
            cold_chain_required_flag=False,
            route_status="Active"
        )
    ]


def generate_scenarios(config: GeneratorConfig, include_all_benchmarks: bool = False) -> List[DimScenario]:
    """
    Generates DimScenario disruption scenario catalog records.
    By default generates SCN-BASE and SCN-A-API-DELAY matching Phase 1 baseline.
    If include_all_benchmarks is True, generates all 5 disruption scenarios (A-E) + baseline.
    """
    base_scenarios = [
        DimScenario(
            scenario_id="SCN-BASE",
            scenario_name="Baseline Plan (Unconstrained)",
            scenario_type="BASELINE",
            scenario_description="Standard baseline operational plan with on-time supplier delivery, scheduled production, and nominal demand.",
            assumptions='{"supplier_delay_days": 0, "qa_hold_days": 0, "demand_multiplier": 1.0}',
            baseline_flag=True,
            synthetic_data_flag=config.synthetic_flag
        ),
        DimScenario(
            scenario_id="SCN-A-API-DELAY",
            scenario_name="Scenario A: 14-Day Critical API Supplier Delay",
            scenario_type="SUPPLIER_DELAY",
            scenario_description="Supplier SUP-001 experiences raw material synthesis bottleneck, delaying API receipt MAT-API-001 by 14 days. Causes plant line stoppage and Week 4 finished goods stockout.",
            assumptions='{"impacted_po": "PO-2026-001", "supplier_id": "SUP-001", "material_sku_id": "MAT-API-001", "slip_days": 14}',
            baseline_flag=False,
            synthetic_data_flag=config.synthetic_flag
        )
    ]

    if not include_all_benchmarks:
        return base_scenarios

    benchmarks = [
        DimScenario(
            scenario_id="SCN-B-BATCH-HOLD",
            scenario_name="Scenario B: 10-Day Finished Batch QA Release Hold",
            scenario_type="QA_HOLD",
            scenario_description="Batch BATCH-AUG-2026-01 triggers OOS investigation and Sterility Retest deviation QEV-2026-001, delaying release by 10 days.",
            assumptions='{"batch_id": "BATCH-AUG-2026-01", "hold_days": 10, "reason": "Sterility_Retest"}',
            baseline_flag=False,
            synthetic_data_flag=config.synthetic_flag
        ),
        DimScenario(
            scenario_id="SCN-C-CARTON-SHORTAGE",
            scenario_name="Scenario C: Shared Packaging Component Shortage",
            scenario_type="MATERIAL_SHORTAGE",
            scenario_description="Supplier SUP-002 carton converting shortage impacts MAT-PKG-CART, simultaneously halting production of both T10 strip and T30 bottle SKUs.",
            assumptions='{"material_sku_id": "MAT-PKG-CART", "impacted_skus": ["SKU-AUG-500-T10", "SKU-AUG-500-T30"]}',
            baseline_flag=False,
            synthetic_data_flag=config.synthetic_flag
        ),
        DimScenario(
            scenario_id="SCN-D-FEFO-EXPOSURE",
            scenario_name="Scenario D: Sub-MARSL Lot Expiry Exposure",
            scenario_type="EXPIRY_RISK",
            scenario_description="Finished inventory lot has RSL < 90 days, breaching customer MARSL acceptance threshold and becoming dead inventory.",
            assumptions='{"lot_id": "LOT-AUG-EXP-01", "rsl_days": 85, "market_marsl": 90}',
            baseline_flag=False,
            synthetic_data_flag=config.synthetic_flag
        ),
        DimScenario(
            scenario_id="SCN-E-CAPACITY-CONFLICT",
            scenario_name="Scenario E: Feasibility Conflict / Plant Line Overload",
            scenario_type="CAPACITY_CONFLICT",
            scenario_description="Proposed PO expediting mitigation requires additional packaging hours, but packaging line is already at 116% utilization.",
            assumptions='{"line_id": "LINE-PLANT1-01", "utilization_pct": 116.0, "status": "INFEASIBLE_CAPACITY"}',
            baseline_flag=False,
            synthetic_data_flag=config.synthetic_flag
        )
    ]
    return base_scenarios + benchmarks


def generate_master_and_bridge_data(config: Optional[GeneratorConfig] = None) -> Dict[str, list]:
    """
    Main generator entry point for Week 03, Day 10.
    Initializes fixed random seed and produces all validated master dimension, bridge,
    and scenario Pydantic v2 records.
    """
    if config is None:
        config = GeneratorConfig()

    init_random_seed(config.random_seed)

    return {
        "dim_product": generate_products(config),
        "dim_finished_sku": generate_finished_skus(config),
        "dim_material": generate_materials(config),
        "dim_supplier": generate_suppliers(config),
        "dim_location": generate_locations(config),
        "dim_customer": generate_customers(config),
        "dim_market": generate_markets(config),
        "dim_production_line": generate_production_lines(config),
        "bridge_bill_of_material": generate_bill_of_materials(config),
        "bridge_supplier_material": generate_supplier_materials(config),
        "bridge_sku_market": generate_sku_markets(config),
        "bridge_location_route": generate_location_routes(config),
        "dim_scenario": generate_scenarios(config)
    }
