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
    cost_per_unit_distance: float = 1.0
    co2_per_unit_distance: float = 0.5

    def calculate_metrics(self, quantity: float) -> tuple[float, float]:
        """Calculate cost and CO2 for moving given quantity"""
        cost = quantity * self.distance * self.cost_per_unit_distance
        co2 = quantity * self.distance * self.co2_per_unit_distance
        return cost, co2
