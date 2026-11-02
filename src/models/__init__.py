"""Central import point for all 33 supply chain control tower data contracts."""

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
from src.models.bridges import (
    BridgeBillOfMaterial,
    BridgeSupplierMaterial,
    BridgeSKUMarket,
    BridgeLocationRoute,
)
from src.models.demand import (
    FactDemandHistory,
    FactCustomerOrder,
)
from src.models.planning import (
    FactDemandForecast,
    FactSupplyPlan,
    FactMaterialRequirement,
    FactInventoryProjection,
)
from src.models.procurement_inventory import (
    FactPurchaseOrder,
    FactInventoryLot,
    FactMaterialConsumption,
)
from src.models.manufacturing_quality import (
    FactProductionOrder,
    FactBatch,
    FactQualityEvent,
)
from src.models.capacity_logistics import (
    FactCapacity,
    FactShipment,
)
from src.models.control_tower import (
    DimScenario,
    FactRiskEvent,
    BridgeRiskEvidence,
    FactRootCause,
    FactMitigationSimulation,
    FactRecommendation,
    DatasetManifest,
)

__all__ = [
    # Master (8)
    "DimProduct", "DimFinishedSKU", "DimMaterial", "DimSupplier",
    "DimLocation", "DimCustomer", "DimMarket", "DimProductionLine",
    # Bridges (4)
    "BridgeBillOfMaterial", "BridgeSupplierMaterial", "BridgeSKUMarket", "BridgeLocationRoute",
    # Demand & Orders (2)
    "FactDemandHistory", "FactCustomerOrder",
    # Planning (4)
    "FactDemandForecast", "FactSupplyPlan", "FactMaterialRequirement", "FactInventoryProjection",
    # Procurement & Stock (3)
    "FactPurchaseOrder", "FactInventoryLot", "FactMaterialConsumption",
    # Manufacturing & QA (3)
    "FactProductionOrder", "FactBatch", "FactQualityEvent",
    # Capacity & Transport (2)
    "FactCapacity", "FactShipment",
    # Control Tower & Scenarios (7)
    "DimScenario", "FactRiskEvent", "BridgeRiskEvidence", "FactRootCause",
    "FactMitigationSimulation", "FactRecommendation", "DatasetManifest"
]

