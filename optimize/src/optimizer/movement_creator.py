# optimizer/movement_planner.py
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from src.models.connection import Connection
from src.models.demand import Demand
from src.models.facility import Facility


class MovementPlanner:
    def __init__(self, facilities: Dict[str, Facility],
                 connections_map: Dict[Tuple[str, str], Connection],
                 valid_connections: Dict[str, Dict[str, str]]):
        self.facilities = facilities
        self.connections_map = connections_map
        self.valid_connections = valid_connections
        self.safety_margin = 0.90  # More conservative safety margin
        self.max_fill_ratio = 0.92  # Maximum target fill ratio
        self.min_movement = 50.0  # Minimum movement size to avoid tiny inefficient movements

    def create_movements(self, current_day: int, active_demands: List[Demand]) -> List[dict]:
        """Create optimized movements for the current day"""
        if current_day == 0 or not active_demands:
            return []

        # Track planned changes to facility levels
        facilities_delta = defaultdict(float)

        # Group demands by customer
        customer_demands = self._group_demands_by_customer(active_demands, current_day)

        # Create movements to satisfy demands
        movements = []
        for customer_id, demands in customer_demands.items():
            total_demand = sum(d.remaining_quantity for d in demands)
            if total_demand <= 0:
                continue

            # Get all possible sources for this customer
            source_options = self._get_source_options(customer_id, total_demand)

            # Create movements from each viable source
            remaining_demand = total_demand
            for source_id, max_quantity in source_options:
                if remaining_demand <= 0:
                    break

                movement = self._create_safe_movement(
                    source_id=source_id,
                    destination_id=customer_id,
                    quantity_needed=remaining_demand,
                    max_quantity=max_quantity,
                    facilities_delta=facilities_delta
                )

                if movement and movement['quantity'] >= self.min_movement:
                    movements.append(movement)
                    remaining_demand -= movement['quantity']
                    # Update planned facility changes
                    facilities_delta[source_id] -= movement['quantity']
                    facilities_delta[customer_id] += movement['quantity']

        return movements

    def _group_demands_by_customer(self, demands: List[Demand],
                                   current_day: int) -> Dict[str, List[Demand]]:
        """Group and prioritize demands by customer"""
        customer_demands = defaultdict(list)

        for demand in demands:
            if (demand.start_delivery_day <= current_day <= demand.end_delivery_day
                    and demand.remaining_quantity > 0):
                customer_demands[demand.customer_id].append(demand)

        # Sort demands within each customer group
        for demands in customer_demands.values():
            demands.sort(key=lambda d: (
                d.end_delivery_day,  # Earlier deadlines first
                -d.remaining_quantity  # Larger quantities first
            ))

        return customer_demands

    def _get_source_options(self, customer_id: str,
                            quantity_needed: float) -> List[Tuple[str, float]]:
        """Get all viable sources for a customer, sorted by desirability"""
        source_options = []

        for source_id, destinations in self.valid_connections.items():
            if customer_id not in destinations:
                continue

            source = self.facilities[source_id]
            if source.current_level <= 0:
                continue

            # Get connection details
            connection = self.connections_map.get((source_id, customer_id))
            if not connection:
                continue

            # Calculate maximum safe quantity from this source
            max_quantity = min(
                source.current_level * self.safety_margin,
                connection.max_capacity * self.safety_margin,
                quantity_needed
            )

            if max_quantity <= 0:
                continue

            # Score this source
            source_score = self._score_source(
                source=source,
                connection=connection,
                quantity=max_quantity
            )

            source_options.append((source_id, max_quantity, source_score))

        # Sort by score (highest first) and return just id and quantity
        return [(s[0], s[1]) for s in
                sorted(source_options, key=lambda x: x[2], reverse=True)]

    def _score_source(self, source: Facility, connection: Connection,
                      quantity: float) -> float:
        """Score a potential source based on multiple factors"""
        # Capacity utilization score (prefer sources with more available capacity)
        utilization = source.current_level / source.capacity
        capacity_score = 1.0 - (abs(0.5 - utilization) * 2)  # Prefer ~50% utilization

        # Connection efficiency score
        cost, co2 = connection.calculate_metrics(quantity)
        efficiency_score = quantity / (cost + co2 + 1.0)  # Add 1.0 to avoid division by zero

        # Lead time score (prefer shorter lead times)
        lead_time_score = 1.0 / (1.0 + connection.lead_time)

        # Combine scores with weights
        return (
                capacity_score * 0.4 +
                efficiency_score * 0.4 +
                lead_time_score * 0.2
        )

    def _create_safe_movement(self, source_id: str, destination_id: str,
                              quantity_needed: float, max_quantity: float,
                              facilities_delta: Dict[str, float]) -> Optional[dict]:
        """Create a safe movement respecting all constraints"""
        source = self.facilities[source_id]
        destination = self.facilities[destination_id]

        # Calculate effective facility levels including planned changes
        source_effective = source.current_level + facilities_delta[source_id]
        dest_effective = destination.current_level + facilities_delta[destination_id]

        # Calculate available capacity considering target maximum
        source_available = source_effective * self.safety_margin
        dest_available = (destination.capacity * self.max_fill_ratio -
                          dest_effective)

        # Calculate safe quantity
        safe_quantity = min(
            quantity_needed,
            source_available,
            dest_available,
            max_quantity
        )

        if safe_quantity < self.min_movement:
            return None

        # Get the connection ID
        connection_id = self.valid_connections[source_id][destination_id]

        return {
            'connection_id': connection_id,
            'quantity': safe_quantity
        }
