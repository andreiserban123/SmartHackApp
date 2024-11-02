# optimizer/advanced_planner.py
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.models.connection import Connection
from src.models.demand import Demand
from src.models.facility import Facility


@dataclass()
class MovementOpportunity:
    score: float = field(compare=True)  # Make score the primary comparison field
    source_id: str = field(compare=False)
    destination_id: str = field(compare=False)
    quantity: float = field(compare=False)
    connection: Connection = field(compare=False)

    def __lt__(self, other):
        # Higher score is better, so reverse comparison
        return self.score > other.score


class AdvancedPlanner:
    def __init__(self, facilities: Dict[str, Facility],
                 connections_map: Dict[Tuple[str, str], Connection],
                 valid_connections: Dict[str, Dict[str, str]]):
        self.facilities = facilities
        self.connections_map = connections_map
        self.valid_connections = valid_connections

        # Configuration
        self.max_fill_ratio = 0.88  # Maximum target fill ratio
        self.min_fill_ratio = 0.15  # Minimum target fill ratio
        self.min_movement = 75.0  # Minimum movement size
        self.max_movements_per_day = 3  # Maximum movements per day

        # Cache network structure
        self._cache_network_structure()

    def create_movements(self, current_day: int, active_demands: List[Demand]) -> List[dict]:
        """Create optimized movements for the current day"""
        if current_day == 0 or not active_demands:
            return []

        # Track planned changes
        facilities_delta = defaultdict(float)
        movements = []

        # Process demands in priority order
        prioritized_demands = self._prioritize_demands(active_demands, current_day)

        # Generate and score movement opportunities
        opportunities = []
        for demand in prioritized_demands:
            if demand.remaining_quantity <= 0:
                continue

            # Get opportunities for this demand
            demand_opportunities = self._generate_opportunities_for_demand(
                demand, facilities_delta
            )
            opportunities.extend(demand_opportunities)

        # Sort opportunities by score (highest first)
        opportunities.sort(reverse=True)

        # Create movements from best opportunities
        movement_count = 0
        processed_connections = set()

        while opportunities and movement_count < self.max_movements_per_day:
            opportunity = opportunities.pop(0)

            # Skip if we've already used this connection
            connection_key = (opportunity.source_id, opportunity.destination_id)
            if connection_key in processed_connections:
                continue

            # Validate movement is still valid
            if self._validate_movement(opportunity, facilities_delta):
                movement = self._create_movement(opportunity)
                movements.append(movement)
                movement_count += 1

                # Update tracking
                facilities_delta[opportunity.source_id] -= opportunity.quantity
                facilities_delta[opportunity.destination_id] += opportunity.quantity
                processed_connections.add(connection_key)

                # Update opportunities list if needed
                opportunities = [
                    opp for opp in opportunities
                    if self._validate_movement(opp, facilities_delta)
                ]

        return movements

    def _cache_network_structure(self):
        """Cache useful network information"""
        # Build source to destination mappings
        self.source_to_dest = defaultdict(list)
        self.dest_to_source = defaultdict(list)

        for (source, dest), conn in self.connections_map.items():
            self.source_to_dest[source].append(dest)
            self.dest_to_source[dest].append(source)

        # Calculate path distances
        self.path_distances = self._calculate_path_distances()

        # Identify key facilities
        self.storage_facilities = {
            fid for fid, f in self.facilities.items()
            if len(self.source_to_dest[fid]) > 2  # Has multiple destinations
               and f.capacity >= 400  # Large storage capacity
        }

    def _calculate_path_distances(self) -> Dict[Tuple[str, str], int]:
        """Calculate minimum path distances between facilities"""
        distances = {}

        def bfs(start: str):
            queue = [(start, 0)]
            seen = {start}

            while queue:
                node, dist = queue.pop(0)
                distances[(start, node)] = dist

                for next_node in self.source_to_dest[node]:
                    if next_node not in seen:
                        seen.add(next_node)
                        queue.append((next_node, dist + 1))

        # Calculate distances from each node
        for facility_id in self.facilities:
            bfs(facility_id)

        return distances

    def _prioritize_demands(self, demands: List[Demand],
                            current_day: int) -> List[Demand]:
        """Prioritize demands based on multiple factors"""
        scored_demands = []

        for demand in demands:
            if demand.remaining_quantity <= 0:
                continue

            # Calculate urgency score
            days_left = demand.end_delivery_day - current_day
            if days_left <= 0:
                urgency = 1.0
            else:
                urgency = 1.0 / (days_left + 1)

            # Calculate efficiency score based on network position
            efficiency = self._calculate_demand_efficiency(demand)

            # Calculate progress score
            progress = 1.0 - (demand.remaining_quantity / demand.quantity)

            # Calculate size score (prefer larger demands)
            size_score = min(1.0, demand.remaining_quantity / 500.0)

            # Combine scores
            score = (
                    urgency * 0.4 +
                    efficiency * 0.3 +
                    progress * 0.2 +
                    size_score * 0.1
            )

            scored_demands.append((score, id(demand), demand))

        # Sort by score and uniqueness key
        return [d for _, _, d in sorted(scored_demands, reverse=True)]

    def _calculate_demand_efficiency(self, demand: Demand) -> float:
        """Calculate how efficiently a demand can be satisfied"""
        customer_id = demand.customer_id

        # Find closest storage facilities
        min_distance = float('inf')
        for source in self.storage_facilities:
            if (source, customer_id) in self.path_distances:
                min_distance = min(min_distance,
                                   self.path_distances[(source, customer_id)])

        if min_distance == float('inf'):
            return 0.0

        return 1.0 / (min_distance + 1)

    def _generate_opportunities_for_demand(self, demand: Demand,
                                           facilities_delta: Dict[str, float]) -> List[MovementOpportunity]:
        """Generate movement opportunities for a specific demand"""
        opportunities = []
        customer_id = demand.customer_id
        needed = demand.remaining_quantity

        # Find all possible sources that can help satisfy this demand
        for source_id in self.dest_to_source[customer_id]:
            source = self.facilities[source_id]

            # Get effective levels
            source_effective = source.current_level + facilities_delta[source_id]
            dest_effective = (self.facilities[customer_id].current_level +
                              facilities_delta[customer_id])

            # Get connection
            connection = self.connections_map.get((source_id, customer_id))
            if not connection:
                continue

            # Calculate safe quantity
            safe_quantity = min(
                needed,
                source_effective * self.max_fill_ratio,
                connection.max_capacity * self.max_fill_ratio,
                (self.facilities[customer_id].capacity * self.max_fill_ratio -
                 dest_effective)
            )

            if safe_quantity < self.min_movement:
                continue

            # Score this opportunity
            score = self._score_opportunity(
                source=source,
                destination=self.facilities[customer_id],
                connection=connection,
                quantity=safe_quantity,
                source_effective=source_effective,
                dest_effective=dest_effective
            )

            opportunity = MovementOpportunity(
                score=score,
                source_id=source_id,
                destination_id=customer_id,
                quantity=safe_quantity,
                connection=connection
            )

            opportunities.append(opportunity)

        return opportunities

    def _score_opportunity(self, source: Facility, destination: Facility,
                           connection: Connection, quantity: float,
                           source_effective: float, dest_effective: float) -> float:
        """Score a movement opportunity based on multiple factors"""
        # Calculate efficiency score
        cost, co2 = connection.calculate_metrics(quantity)
        efficiency_score = quantity / (cost + co2 + 1.0)

        # Calculate utilization improvement
        current_src_util = source_effective / source.capacity
        current_dst_util = dest_effective / destination.capacity

        new_src_util = (source_effective - quantity) / source.capacity
        new_dst_util = (dest_effective + quantity) / destination.capacity

        # Prefer movements that balance utilization
        utilization_score = (
                abs(0.5 - current_src_util) - abs(0.5 - new_src_util) +
                abs(0.5 - current_dst_util) - abs(0.5 - new_dst_util)
        )

        # Calculate lead time penalty
        lead_time_score = 1.0 / (1.0 + connection.lead_time)

        # Calculate quantity bonus (prefer larger movements)
        quantity_score = min(1.0, quantity / connection.max_capacity)

        # Combine scores
        return (
                efficiency_score * 0.3 +
                utilization_score * 0.3 +
                lead_time_score * 0.2 +
                quantity_score * 0.2
        )

    def _validate_movement(self, opportunity: MovementOpportunity,
                           facilities_delta: Dict[str, float]) -> bool:
        """Validate a movement is still valid with current state"""
        source = self.facilities[opportunity.source_id]
        destination = self.facilities[opportunity.destination_id]

        # Get effective levels
        source_effective = source.current_level + facilities_delta[opportunity.source_id]
        dest_effective = destination.current_level + facilities_delta[opportunity.destination_id]

        # Validate capacity constraints
        if source_effective - opportunity.quantity < source.capacity * self.min_fill_ratio:
            return False

        if dest_effective + opportunity.quantity > destination.capacity * self.max_fill_ratio:
            return False

        return True

    def _create_movement(self, opportunity: MovementOpportunity) -> dict:
        """Create movement dictionary from opportunity"""
        connection_id = self.valid_connections[opportunity.source_id][opportunity.destination_id]

        return {
            'connection_id': connection_id,
            'quantity': opportunity.quantity
        }
