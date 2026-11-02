import datetime
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class GeneratorConfig:
    random_seed: int = 20261014
    
    # Temporal horizons (Weekly buckets starting on Monday)
    history_weeks: int = 104
    future_weeks: int = 26
    
    # As-of planning cutoff date: Monday, October 26, 2026
    planning_as_of_date: datetime.date = datetime.date(2026, 10, 26)
    
    @property
    def history_start_date(self) -> datetime.date:
        return self.planning_as_of_date - datetime.timedelta(weeks=self.history_weeks)
        
    @property
    def future_end_date(self) -> datetime.date:
        return self.planning_as_of_date + datetime.timedelta(weeks=self.future_weeks)

    # Output targets
    output_db_path: str = "data/processed/control_tower.db"
    output_parquet_dir: str = "data/processed/parquet"
    output_csv_dir: str = "data/processed/csv"
    output_manifest_path: str = "data/processed/dataset_manifest.json"
    
    # Phase 1 Scope specifications
    product_family: str = "Augmentin"
    currency: str = "INR"
    synthetic_flag: bool = True

