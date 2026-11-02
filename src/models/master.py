"""
Master Data Domain Entities (8 Entities).
Technical Specification & Pydantic v2 Schemas for Week 02, Day 05 Deliverable.

Defines the relational master entities representing products, SKUs, materials,
suppliers, facilities, customers, regional markets, and production lines.
All models enforce strict field validation, ranges, and data provenance tracking.
"""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class StorageCondition(str, Enum):
    AMBIENT = "Ambient"
    CONTROLLED_ROOM_TEMP = "Controlled Room Temperature (15-25C)"
    REFRIGERATED = "Refrigerated (2-8C)"
    FROZEN = "Frozen (-20C)"


class LocationType(str, Enum):
    MANUFACTURING_PLANT = "MANUFACTURING_PLANT"
    DISTRIBUTION_CENTRE = "DISTRIBUTION_CENTRE"
    SUPPLIER = "SUPPLIER"
    MARKET = "MARKET"
    QC_LAB = "QC_LAB"


class SupplierRiskTier(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class CustomerType(str, Enum):
    HOSPITAL = "Hospital"
    WHOLESALER = "Wholesaler"
    PHARMACY_CHAIN = "Pharmacy Chain"
    GOVERNMENT_TENDER = "Government Tender"


class ServicePriority(str, Enum):
    TIER_1 = "Tier-1"
    TIER_2 = "Tier-2"
    TIER_3 = "Tier-3"


class DimProduct(BaseModel):
    """
    Tier 1 Master Entity: Commercial product family or brand grouping.
    Grain: One record per product family.
    """
    product_id: str = Field(..., min_length=3, description="Unique product family identifier, e.g. PRD-AUG")
    product_name: str = Field(..., min_length=2, description="Commercial family name, e.g. Augmentin")
    product_family: str = Field(..., min_length=2, description="Therapeutic family group, e.g. Antibiotic-Penicillin")
    therapy_area: str = Field(..., min_length=2, description="Clinical classification, e.g. Anti-Infectives")
    critical_medicine_flag: bool = Field(default=True, description="Raises prioritisation in risk calculations")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("product_id cannot be empty or whitespace")
        return v.strip()


class DimFinishedSKU(BaseModel):
    """
    Tier 3 Master Entity: Sellable pack-level finished commercial presentation.
    Grain: One record per distinct finished SKU pack format.
    """
    finished_sku_id: str = Field(..., min_length=3, description="Pack-level sellable SKU ID, e.g. SKU-AUG-500-T10")
    product_id: str = Field(..., min_length=3, description="Foreign key to dim_product.product_id")
    sku_description: str = Field(..., min_length=5, description="Sellable presentation description")
    dosage_form: str = Field(..., min_length=2, description="Dosage form: Tablet, Capsule, Suspension, etc.")
    strength: str = Field(..., min_length=2, description="Strength label, e.g. 500mg/125mg")
    pack_configuration: str = Field(..., min_length=3, description="Pack configuration: 10-Tablet Strip, 30-Tablet Bottle, etc.")
    shelf_life_days: int = Field(default=730, gt=0, description="Synthetic approved shelf life in days (must be > 0)")
    storage_condition: str = Field(default="Ambient", description="Ambient, Refrigerated, or Frozen")
    launch_date: date = Field(..., description="Commercial launch date of the SKU")
    status: str = Field(default="Active", description="Active, Phase-Out, or Discontinued")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")

    @field_validator("shelf_life_days")
    @classmethod
    def validate_shelf_life(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("shelf_life_days must be strictly positive")
        return v


class DimMaterial(BaseModel):
    """
    Tier 4 Master Entity: Raw chemical active ingredient, excipient, or packaging component.
    Grain: One record per component material SKU.
    """
    material_sku_id: str = Field(..., min_length=3, description="Unique material component identifier, e.g. MAT-API-001")
    material_name: str = Field(..., min_length=3, description="Material description, e.g. Amoxicillin Trihydrate API")
    material_type: str = Field(..., min_length=2, description="API, Excipient, Coating, Blister Foil, Bottle, Carton, Leaflet")
    unit_of_measure: str = Field(..., min_length=1, description="kg, g, units, rolls, etc.")
    shelf_life_days: int = Field(default=540, gt=0, description="Component shelf life in days")
    retest_interval_days: Optional[int] = Field(default=365, gt=0, description="Retest window for APIs/excipients")
    release_time_days: int = Field(default=5, ge=0, description="Inbound QC release testing lead time in days")
    critical_material_flag: bool = Field(default=True, description="Single point of failure indicator")
    storage_condition: str = Field(default="Ambient", description="Storage temperature requirement")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")

    @field_validator("release_time_days")
    @classmethod
    def validate_release_time(cls, v: int) -> int:
        if v < 0:
            raise ValueError("release_time_days cannot be negative")
        return v


class DimSupplier(BaseModel):
    """
    External Vendor Master Entity: Suppliers providing active ingredients, excipients, and packaging.
    Grain: One record per vendor organization.
    """
    supplier_id: str = Field(..., min_length=3, description="Fictional supplier ID, e.g. SUP-001")
    supplier_name: str = Field(..., min_length=3, description="Fictional business name, e.g. Deccan Active Pharma Chem")
    supplier_type: str = Field(..., min_length=3, description="API Manufacturer, Packaging Supplier, Excipient Vendor, or CMO")
    default_lead_time_days: int = Field(default=21, gt=0, description="Standard supplier procurement lead time in days")
    minimum_order_quantity: float = Field(default=100.0, ge=0.0, description="MOQ in material base UOM")
    order_multiple: float = Field(default=50.0, gt=0.0, description="Order increment multiple")
    otif_target: float = Field(default=95.0, ge=0.0, le=100.0, description="Contractual SLA on-time in-full percentage (0-100)")
    risk_tier: str = Field(default="Medium", description="Low, Medium, or High risk tier")
    single_source_dependency_flag: bool = Field(default=False, description="Single-source dependency indicator")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")

    @field_validator("otif_target")
    @classmethod
    def validate_otif(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError("otif_target must be between 0.0 and 100.0 percent")
        return v


class DimLocation(BaseModel):
    """
    Network Topology Node Entity: Facilities across manufacturing, warehousing, and commercial tiers.
    Grain: One record per geographic network facility node.
    """
    location_id: str = Field(..., min_length=3, description="Unique network node identifier, e.g. LOC-PLANT-01")
    location_name: str = Field(..., min_length=3, description="Facility name, e.g. Plant Alpha Hyderabad")
    location_type: str = Field(..., min_length=3, description="MANUFACTURING_PLANT, DISTRIBUTION_CENTRE, SUPPLIER, or MARKET")
    city: str = Field(..., min_length=2, description="Real Indian city: Hyderabad, Pune, Nagpur, Ahmedabad, etc.")
    state: str = Field(..., min_length=2, description="Real Indian state: Telangana, Maharashtra, Gujarat, etc.")
    country: str = Field(default="India", description="Country of operations")
    capacity: float = Field(default=50000.0, ge=0.0, description="Nominal weekly capacity throughput in base units")
    cold_chain_capable: bool = Field(default=False, description="Refrigerated cold-chain storage capability flag")
    synthetic_entity_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")


class DimCustomer(BaseModel):
    """
    Commercial Demand Entity: Institutional hospital networks, wholesalers, and retail pharmacies.
    Grain: One record per purchasing customer account.
    """
    customer_id: str = Field(..., min_length=3, description="Fictional customer identifier, e.g. CUST-001")
    customer_name: str = Field(..., min_length=3, description="Customer organization name, e.g. Deccan Apex Hospital Network")
    market_id: str = Field(..., min_length=3, description="Foreign key to dim_market.market_id")
    customer_type: str = Field(..., min_length=3, description="Hospital, Wholesaler, Pharmacy Chain, or Government Tender")
    service_priority: str = Field(default="Tier-1", description="Tier-1, Tier-2, Tier-3 service SLA priority")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")


class DimMarket(BaseModel):
    """
    Geographic Demand Zone Entity: Regional metropolitan markets aggregating customer consumption.
    Grain: One record per regional commercial market.
    """
    market_id: str = Field(..., min_length=3, description="Unique demand market ID, e.g. MKT-IN-HYD")
    market_name: str = Field(..., min_length=3, description="Market name, e.g. Hyderabad Metro & Telangana Zone")
    city: str = Field(..., min_length=2, description="Anchor city")
    state: str = Field(..., min_length=2, description="State of jurisdiction")
    region: str = Field(..., min_length=2, description="Geographic zone: South, West, North, East")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")


class DimProductionLine(BaseModel):
    """
    Manufacturing Capacity Entity: Specific formulation, tableting, and packaging lines in plants.
    Grain: One record per physical manufacturing or packaging line.
    """
    production_line_id: str = Field(..., min_length=3, description="Unique production line ID, e.g. LINE-PLANT1-01")
    location_id: str = Field(..., min_length=3, description="Foreign key to dim_location.location_id (MANUFACTURING_PLANT)")
    line_name: str = Field(..., min_length=3, description="Line description, e.g. Oral Solid Dosage Granulation Line")
    capacity_unit: str = Field(default="hours_per_week", description="Throughput capacity unit")
    standard_rate: float = Field(default=5000.0, gt=0.0, description="Standard units/packs produced per operating hour")
    supported_product_group: str = Field(..., min_length=3, description="Compatible product group, e.g. Solid Oral Antibiotics")
    maintenance_constraints: str = Field(
        default="Scheduled maintenance on alternate Sundays",
        description="Routine maintenance window and changeover constraints"
    )

    @field_validator("standard_rate")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("standard_rate must be strictly positive")
        return v
