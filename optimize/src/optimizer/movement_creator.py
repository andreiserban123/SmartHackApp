from typing import List

from src.models.demand import Demand


class MovementCreator:
    def __init__(self, data: dict, connections_map: dict):
        self.data = data
        self.connections_map = connections_map

    def create_movements(self, current_day: int, active_demands: List[Demand]) -> List[dict]:
        """Create optimized movements for the current day"""
        if current_day == 0:
            print(f"Day 0 - Active demands: {len(active_demands)}")
            return []

        movements = []

        # Get active demands
        active_demands = [d for d in active_demands
                          if d.remaining_quantity > 0 and
                          d.start_delivery_day <= current_day <= d.end_delivery_day]

        print(f"Day {current_day} - Processing {len(active_demands)} active demands")

        if not active_demands:
            return movements

        # Track tank inventory
        tank_inventory = {}
        for _, tank in self.data['tanks'].iterrows():
            tank_inventory[tank['id']] = float(tank['initial_stock'])

        # Sort demands by urgency and size
        active_demands.sort(key=lambda x: (
            (x.end_delivery_day - current_day),  # Days until deadline
            -(x.end_delivery_day - x.start_delivery_day),  # Smaller delivery window first
            -x.remaining_quantity  # Larger quantities first
        ))

        # Process each demand
        for demand in active_demands:
            print(f"Processing demand {demand.id}: {demand.remaining_quantity} units needed")

            customer = self.data['customers'][
                self.data['customers']['id'] == demand.customer_id].iloc[0]
            max_customer_input = float(customer['max_input'])

            potential_moves = self._find_potential_moves(
                demand, customer, tank_inventory, current_day, max_customer_input)

            # Create movements from best options
            for move in potential_moves:
                if demand.remaining_quantity <= 0:
                    break

                quantity = min(move['quantity'], demand.remaining_quantity)

                if quantity > 0:
                    movement = {
                        'connection_id': move['connection'].id,
                        'quantity': quantity,
                        'delivery_day': current_day
                    }
                    movements.append(movement)

                    # Update tracking
                    tank_inventory[move['tank_id']] -= quantity
                    demand.remaining_quantity -= quantity
                    print(f"Created movement: {quantity} units from {move['tank_id']}")

        print(f"Created {len(movements)} movements")
        return movements

    def _find_potential_moves(self, demand, customer, tank_inventory, current_day, max_customer_input):
        """Find and sort potential moves for a demand"""
        potential_moves = []

        for _, tank in self.data['tanks'].iterrows():
            if tank['node_type'] != 'STORAGE_TANK':
                continue

            connection_key = (tank['id'], demand.customer_id)
            if connection_key not in self.connections_map:
                continue

            connection = self.connections_map[connection_key]

            # Calculate available quantity
            available_stock = tank_inventory[tank['id']]
            max_quantity = min(
                demand.remaining_quantity,
                available_stock,
                connection.max_capacity,
                float(tank['max_output']),
                max_customer_input
            )

            if max_quantity <= 0:
                continue

            # Calculate delivery timing and costs
            delivery_time = current_day + connection.lead_time
            transport_cost = connection.distance * connection.cost_per_unit_distance
            early_days = max(0, demand.start_delivery_day - delivery_time)
            late_days = max(0, delivery_time - demand.end_delivery_day)

            total_cost = transport_cost * max_quantity

            potential_moves.append({
                'tank_id': tank['id'],
                'connection': connection,
                'quantity': max_quantity,
                'total_cost': total_cost,
                'delivery_time': delivery_time,
                'is_on_time': (early_days == 0 and late_days == 0)
            })

        # Sort potential moves
        potential_moves.sort(key=lambda x: (
            not x['is_on_time'],  # Prioritize on-time deliveries
            x['total_cost'] / x['quantity']  # Then minimize cost per unit
        ))

        return potential_moves
