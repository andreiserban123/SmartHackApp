import time

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import requests
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Constants
API_KEY = "7bcd6334-bc2e-4cbf-b9d4-61cb9e868869"
BASE_URL = "http://localhost:8080/api/v1"
TOTAL_DAYS = 42


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


@dataclass
class Demand:
    id: str
    customer_id: str
    quantity: float
    post_day: int
    start_delivery_day: int
    end_delivery_day: int
    remaining_quantity: float = None

    def __post_init__(self):
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity


class SupplyChainOptimizer:
    def __init__(self):
        self.session_id = None
        self.current_day = 0
        self.data = self._load_data()
        self.active_demands: List[Demand] = []
        self.connections_map: Dict[Tuple[str, str], Connection] = {}

    def _load_data(self) -> dict:
        """Load and prepare all necessary data"""
        # First try to find data relative to the current file
        possible_paths = [
            Path("data"),  # Local data directory
            Path("../data"),  # One level up
            Path("../../data"),  # Two levels up
        ]

        data_dir = None
        for path in possible_paths:
            if path.exists() :
                data_dir = path
                break

        if not data_dir:
            print("Could not find data directory. Tried:")
            for path in possible_paths:
                print(f"- {path.absolute()}")
            print("\nCurrent working directory:", Path.cwd())
            print("\nAvailable directories:", [d for d in Path().glob("*") if d.is_dir()])
            raise FileNotFoundError("Data directory not found")

        print(f"\nLoading data from {data_dir}")

        try:
            # Load CSV files with error handling
            print("\nLoading refineries.csv...")
            refineries = pd.read_csv(data_dir / "refineries.csv", sep=';')
            print(f"Loaded {len(refineries)} refineries")
            print("First refinery example:")
            print(refineries.iloc[0])

            print("\nLoading tanks.csv...")
            tanks = pd.read_csv(data_dir / "tanks.csv", sep=';')
            print(f"Loaded {len(tanks)} tanks")
            print("First tank example:")
            print(tanks.iloc[0])

            print("\nLoading customers.csv...")
            customers = pd.read_csv(data_dir / "customers.csv", sep=';')
            print(f"Loaded {len(customers)} customers")
            print("First customer example:")
            print(customers.iloc[0])

            print("\nLoading demands.csv...")
            demands = pd.read_csv(data_dir / "demands.csv", sep=';')
            print(f"Loaded {len(demands)} demands")
            print("First demand example:")
            print(demands.iloc[0])

            # Convert demands to internal format
            demands_list = []
            for _, row in demands.iterrows():
                demands_list.append(Demand(
                    id=row['id'],
                    customer_id=row['customer_id'],
                    quantity=row['quantity'],
                    post_day=row['post_day'],
                    start_delivery_day=row['start_delivery_day'],
                    end_delivery_day=row['end_delivery_day']
                ))

            return {
                'refineries': refineries,
                'tanks': tanks,
                'customers': customers,
                'demands': demands_list
            }
        except Exception as e:
            print(f"\nError loading data: {e}")
            if isinstance(e, pd.errors.EmptyDataError):
                print("One of the CSV files is empty")
            elif isinstance(e, pd.errors.ParserError):
                print("Error parsing CSV file - check the file format and separator")
            raise

    def cleanup_existing_session(self):
        """End any existing session"""
        headers = {
            'API-KEY': API_KEY,
            'Content-Type': 'application/json'
        }

        try:
            print("Attempting to clean up existing session...")
            response = requests.post(f"{BASE_URL}/session/end", headers=headers)
            if response.status_code == 200:
                print("Successfully cleaned up existing session")
                return True
            elif response.status_code == 404:
                print("No existing session to clean up")
                return True
            else:
                print(f"Failed to clean up session: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            print(f"Error cleaning up session: {e}")
            return False

    def start_session(self):
        """Start a new game session"""
        # First, try to clean up any existing session
        if not self.cleanup_existing_session():
            print("Warning: Failed to clean up existing session")

        headers = {
            'API-KEY': API_KEY,
            'Content-Type': 'application/json'
        }

        try:
            print("\nStarting new session...")
            response = requests.post(f"{BASE_URL}/session/start", headers=headers)

            if response.status_code == 200:
                self.session_id = response.text.strip('"')
                if self.session_id:
                    print(f"Session started successfully: {self.session_id}")
                    return True
                else:
                    print("Error: Session ID not found in response")
                    return False
            else:
                print(f"Failed to start session: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Network error starting session: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error starting session: {e}")
            return False

    def create_movements(self) -> List[dict]:
        """Create optimized movements for the current day"""
        if self.current_day == 0:
            return []

        movements = []
        active_demands = [d for d in self.active_demands
                          if d.remaining_quantity > 0 and
                          d.start_delivery_day <= self.current_day <= d.end_delivery_day]

        # Sort demands by urgency (closest to end delivery day) and size
        active_demands.sort(key=lambda x: (x.end_delivery_day - self.current_day, -x.quantity))

        # Track tank levels as we create movements
        tank_levels = {}
        for tank in self.data['tanks'].itertuples():
            tank_levels[tank.id] = tank.initial_stock

        # Process each demand
        for demand in active_demands:
            customer_id = demand.customer_id
            required_quantity = demand.remaining_quantity

            # Find customer max input capacity
            customer = self.data['customers'][self.data['customers']['id'] == customer_id].iloc[0]
            max_customer_input = float(customer['max_input'])

            # Find all tanks that can reach this customer
            potential_sources = []
            for tank in self.data['tanks'].itertuples():
                if tank.node_type != 'STORAGE_TANK':
                    continue

                # Check if there's a connection to this customer
                connection = self.connections_map.get((tank.id, customer_id))
                if not connection:
                    continue

                # Calculate available quantity from this tank
                available_quantity = min(
                    tank_levels[tank.id],  # Current tank level
                    float(tank.max_output),  # Tank output constraint
                    float(connection.max_capacity),  # Connection capacity
                    required_quantity,  # Demand remaining
                    max_customer_input  # Customer input constraint
                )

                if available_quantity > 0:
                    # Calculate delivery time
                    delivery_time = self.current_day + connection.lead_time

                    # Calculate if delivery would be early or late
                    early_penalty = max(0, demand.start_delivery_day - delivery_time)
                    late_penalty = max(0, delivery_time - demand.end_delivery_day)

                    # Calculate total cost per unit
                    cost_per_unit = (
                            connection.cost_per_unit_distance * connection.distance +  # Transport cost
                            early_penalty * float(customer.early_delivery_penalty) +  # Early penalty
                            late_penalty * float(customer.late_delivery_penalty)  # Late penalty
                    )

                    potential_sources.append({
                        'tank_id': tank.id,
                        'connection': connection,
                        'available_quantity': available_quantity,
                        'cost_per_unit': cost_per_unit,
                        'co2_per_unit': connection.co2_per_unit_distance * connection.distance,
                        'delivery_time': delivery_time
                    })

            # Sort potential sources by cost and CO2 impact
            potential_sources.sort(key=lambda x: (
                max(0, x['delivery_time'] - demand.end_delivery_day),  # Prioritize on-time delivery
                x['cost_per_unit'],  # Then by cost
                x['co2_per_unit']  # Then by CO2 emissions
            ))

            # Create movements from best sources until demand is met
            remaining_demand = required_quantity
            for source in potential_sources:
                if remaining_demand <= 0:
                    break

                movement_quantity = min(source['available_quantity'], remaining_demand)

                if movement_quantity > 0:
                    movement = {
                        'connection_id': source['connection'].id,
                        'quantity': movement_quantity,
                        'delivery_day': self.current_day
                    }
                    movements.append(movement)

                    # Update tracking
                    tank_levels[source['tank_id']] -= movement_quantity
                    remaining_demand -= movement_quantity

        return movements

    def make_move(self, movements: List[dict]) -> dict:
        """Submit move for the current day"""
        if not self.session_id:
            print("No active session")
            return None

        headers = {
            'API-KEY': API_KEY,
            'SESSION-ID': self.session_id,
            'Content-Type': 'application/json'
        }

        data = {
            'day': self.current_day,
            'movements': movements
        }

        try:
            response = requests.post(f"{BASE_URL}/play/round", headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()

                # Update internal state
                self._update_state(result)

                return result
            else:
                print(f"Error making move: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error making move: {e}")
            return None

    def _update_state(self, response: dict):
        """Update internal state based on API response"""
        # Update day
        self.current_day += 1

        # Add new demands
        for demand in response.get('demands', []):
            self.active_demands.append(Demand(**demand))

        # Process penalties
        self._process_penalties(response.get('penalties', []))

        # Update KPIs
        self._update_kpis(response.get('deltaKpis', {}), response.get('totalKpis', {}))

    def _process_penalties(self, penalties: List[dict]):
        """Process and analyze penalties"""
        penalty_types = {}
        for penalty in penalties:
            penalty_type = penalty['type']
            if penalty_type not in penalty_types:
                penalty_types[penalty_type] = {
                    'count': 0,
                    'total_cost': 0,
                    'total_co2': 0
                }
            penalty_types[penalty_type]['count'] += 1
            penalty_types[penalty_type]['total_cost'] += penalty['cost']
            penalty_types[penalty_type]['total_co2'] += penalty['co2']

        # Print penalty summary
        if penalty_types:
            print("\nPenalties this round:")
            for ptype, stats in penalty_types.items():
                print(f"{ptype}: {stats['count']} occurrences, "
                      f"Cost: {stats['total_cost']:.2f}, "
                      f"CO2: {stats['total_co2']:.2f}")

    def _update_kpis(self, delta_kpis: dict, total_kpis: dict):
        """Update and display KPIs"""
        print(f"\nDay {self.current_day} KPIs:")
        print(f"Delta - Cost: {delta_kpis.get('cost', 0):.2f}, "
              f"CO2: {delta_kpis.get('co2', 0):.2f}")
        print(f"Total - Cost: {total_kpis.get('cost', 0):.2f}, "
              f"CO2: {total_kpis.get('co2', 0):.2f}")

    def run(self):
        """Run the complete optimization"""
        print("\nStarting Supply Chain Optimization")
        print("=================================")
        print(f"API URL: {BASE_URL}")
        print(f"API Key: {API_KEY[:8]}...")

        # Start new session with retry
        max_retries = 3
        for attempt in range(max_retries):
            if self.start_session():
                break
            else:
                if attempt < max_retries - 1:
                    print(f"Retrying session start ({attempt + 2}/{max_retries})...")
                    time.sleep(2)  # Wait 2 seconds before retry
                else:
                    print("Failed to start session after all retries")
                    return

        # Run optimization
        try:
            while self.current_day < TOTAL_DAYS:
                print(f"\nProcessing day {self.current_day}")
                movements = self.create_movements()
                result = self.make_move(movements)

                if not result:
                    print("Error occurred, stopping simulation")
                    break

                # Print daily summary
                if movements:
                    print(f"Submitted {len(movements)} movements")
                else:
                    print("No movements submitted")
        except KeyboardInterrupt:
            print("\nOptimization interrupted by user")
        except Exception as e:
            print(f"\nError during optimization: {e}")
        finally:
            # Always try to end session cleanly
            if self.session_id:
                self.cleanup_existing_session()


def main():
    optimizer = SupplyChainOptimizer()
    optimizer.run()


if __name__ == "__main__":
    main()