from dataclasses import dataclass


@dataclass
class Connection:
    id: str
    source_id: str
    destination_id: str
    transport_type: str  # 'PIPELINE' or 'TRUCK'
    lead_time: int
    max_capacity: float
    distance: float
    cost_per_unit_distance: float
    co2_per_unit_distance: float
