import datetime
from typing import List, Dict, Tuple
from src.generator.config import GeneratorConfig
from src.models.master import (
    DimProduct, DimFinishedSKU, DimMaterial, DimSupplier,
    DimLocation, DimCustomer, DimMarket, DimProductionLine
)
from src.models.bridges import (
    BridgeBillOfMaterial, BridgeSupplierMaterial, BridgeSKUMarket, BridgeLocationRoute
)
from src.models.control_tower import DimScenario

def generate_master_and_bridge_data(config: GeneratorConfig) -> Dict[str, list]:
    """Generates all Phase 1 Master, Bridge, and Scenario records."""
    
    # 1. dim_product
    products = [
        DimProduct(
            product_id="PRD-AUG",
            product_name="Augmentin",
            product_family="Antibiotic-Penicillin",
            therapy_area="Anti-Infectives",
            critical_medicine_flag=True,
            synthetic_data_flag=config.synthetic_flag
        )
    ]
    
    # 2. dim_finished_sku (2 configurations: 10-tablet strip and 30-tablet bottle)
    skus = [
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
    
    # 3. dim_material (API, Excipient, Blister, Bottle, Carton)
    materials = [
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
            shelf_life_days=720,
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
            shelf_life_days=1095,
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
            shelf_life_days=1095,
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
            shelf_life_days=730,
            retest_interval_days=None,
            release_time_days=2,
            critical_material_flag=True,
            storage_condition="Ambient",
            synthetic_data_flag=config.synthetic_flag
        )
    ]
    
    # 4. dim_supplier
    suppliers = [
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
    
    # 5. dim_location (Nodes)
    locations = [
        DimLocation(
            location_id="LOC-SUP-01",
            location_name="Deccan API Synthesis Plant",
            location_type="SUPPLIER",
            city="Ahmedabad",
            state="Gujarat",
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
            capacity=0.0,
            cold_chain_capable=False,
            synthetic_entity_flag=config.synthetic_flag
        )
    ]
    
    # 6. dim_market
    markets = [
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
    
    # 7. dim_customer
    customers = [
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
    
    # 8. dim_production_line
    production_lines = [
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
    
    # 9. bridge_bill_of_material (BOM)
    # Note: 1 pack of T10 contains 10 tablets = 6.25g API (0.00625 kg) + 0.002 kg excipient + 1 blister + 1 carton
    # 1 pack of T30 contains 30 tablets = 18.75g API (0.01875 kg) + 0.006 kg excipient + 1 bottle + 1 carton
    bom_records = [
        # SKU-AUG-500-T10
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-01",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-API-001",
            quantity_per_finished_unit=0.00625,  # 6.25g API per 10-tablet pack
            scrap_factor_pct=2.0,
            effective_start_date=datetime.date(2023, 1, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-02",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-EXC-001",
            quantity_per_finished_unit=0.00200,  # 2.0g excipient per pack
            scrap_factor_pct=1.5,
            effective_start_date=datetime.date(2023, 1, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-03",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-PKG-BLIST",
            quantity_per_finished_unit=1.0,  # 1 blister strip
            scrap_factor_pct=1.0,
            effective_start_date=datetime.date(2023, 1, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T10-04",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-PKG-CART",
            quantity_per_finished_unit=1.0,  # 1 outer carton
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
            quantity_per_finished_unit=0.01875,  # 18.75g API per 30-tablet pack
            scrap_factor_pct=2.0,
            effective_start_date=datetime.date(2023, 6, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T30-02",
            finished_sku_id="SKU-AUG-500-T30",
            material_sku_id="MAT-EXC-001",
            quantity_per_finished_unit=0.00600,  # 6.0g excipient per pack
            scrap_factor_pct=1.5,
            effective_start_date=datetime.date(2023, 6, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T30-03",
            finished_sku_id="SKU-AUG-500-T30",
            material_sku_id="MAT-PKG-BOTT",
            quantity_per_finished_unit=1.0,  # 1 HDPE bottle
            scrap_factor_pct=1.0,
            effective_start_date=datetime.date(2023, 6, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-AUG-T30-04",
            finished_sku_id="SKU-AUG-500-T30",
            material_sku_id="MAT-PKG-CART",
            quantity_per_finished_unit=1.0,  # 1 outer carton (shared material!)
            scrap_factor_pct=1.0,
            effective_start_date=datetime.date(2023, 6, 1),
            bom_version="V1",
            synthetic_data_flag=config.synthetic_flag
        )
    ]
    
    # 10. bridge_supplier_material
    supplier_materials = [
        BridgeSupplierMaterial(
            supplier_id="SUP-001",
            material_sku_id="MAT-API-001",
            supplier_lead_time_days=21,
            minimum_order_quantity=100.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        ),
        BridgeSupplierMaterial(
            supplier_id="SUP-001",
            material_sku_id="MAT-EXC-001",
            supplier_lead_time_days=14,
            minimum_order_quantity=200.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        ),
        BridgeSupplierMaterial(
            supplier_id="SUP-002",
            material_sku_id="MAT-PKG-BLIST",
            supplier_lead_time_days=14,
            minimum_order_quantity=5000.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        ),
        BridgeSupplierMaterial(
            supplier_id="SUP-002",
            material_sku_id="MAT-PKG-BOTT",
            supplier_lead_time_days=14,
            minimum_order_quantity=5000.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        ),
        BridgeSupplierMaterial(
            supplier_id="SUP-002",
            material_sku_id="MAT-PKG-CART",
            supplier_lead_time_days=14,
            minimum_order_quantity=5000.0,
            approved_supplier_flag=True,
            supplier_priority=1,
            effective_start_date=datetime.date(2023, 1, 1)
        )
    ]
    
    # 11. bridge_sku_market
    sku_markets = [
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T10",
            market_id="MKT-IN-HYD",
            market_priority=1,
            service_level_target=98.0,
            effective_start_date=datetime.date(2023, 1, 15)
        ),
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T10",
            market_id="MKT-IN-PUN",
            market_priority=1,
            service_level_target=98.0,
            effective_start_date=datetime.date(2023, 1, 15)
        ),
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T30",
            market_id="MKT-IN-HYD",
            market_priority=1,
            service_level_target=95.0,
            effective_start_date=datetime.date(2023, 6, 1)
        ),
        BridgeSKUMarket(
            finished_sku_id="SKU-AUG-500-T30",
            market_id="MKT-IN-PUN",
            market_priority=1,
            service_level_target=95.0,
            effective_start_date=datetime.date(2023, 6, 1)
        )
    ]
    
    # 12. bridge_location_route
    routes = [
        # Plant Alpha -> Central DC Nagpur
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
        # Central DC Nagpur -> Market Hyderabad
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
        # Central DC Nagpur -> Market Pune
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
    
    # 13. dim_scenario
    scenarios = [
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
    
    return {
        "dim_product": products,
        "dim_finished_sku": skus,
        "dim_material": materials,
        "dim_supplier": suppliers,
        "dim_location": locations,
        "dim_customer": customers,
        "dim_market": markets,
        "dim_production_line": production_lines,
        "bridge_bill_of_material": bom_records,
        "bridge_supplier_material": supplier_materials,
        "bridge_sku_market": sku_markets,
        "bridge_location_route": routes,
        "dim_scenario": scenarios
    }

