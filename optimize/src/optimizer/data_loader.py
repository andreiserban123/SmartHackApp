from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from src.models.connection import Connection
from src.models.demand import Demand


class DataLoader:
    @staticmethod
    def load_data(possible_paths: List[Path] = None) -> dict:
        """Load and prepare all necessary data"""
        if possible_paths is None:
            possible_paths = [
                Path("data"),  # Local data directory
                Path("../data"),  # One level up
                Path("../../data"),  # Two levels up
            ]

        data_dir = None
        for path in possible_paths:
            if path.exists():
                data_dir = path
                break

        if not data_dir:
            raise FileNotFoundError("Data directory not found")

        try:
            print("\nLoading data files...")

            # Load CSV files
            refineries = pd.read_csv(data_dir / "refineries.csv", sep=';')
            tanks = pd.read_csv(data_dir / "tanks.csv", sep=';')
            customers = pd.read_csv(data_dir / "customers.csv", sep=';')
            demands = pd.read_csv(data_dir / "demands.csv", sep=';')
            connections = pd.read_csv(data_dir / "connections.csv", sep=';')

            print(f"Loaded: {len(refineries)} refineries, {len(tanks)} tanks, "
                  f"{len(customers)} customers, {len(demands)} demands, "
                  f"{len(connections)} connections")

            # Convert demands to internal format
            demands_list = []
            initial_demands = []
            for _, row in demands.iterrows():
                demand = Demand(
                    id=row['id'],
                    customer_id=row['customer_id'],
                    quantity=row['quantity'],
                    post_day=row['post_day'],
                    start_delivery_day=row['start_delivery_day'],
                    end_delivery_day=row['end_delivery_day']
                )
                demands_list.append(demand)
                if row['post_day'] == 0:
                    initial_demands.append(demand)

            return {
                'refineries': refineries,
                'tanks': tanks,
                'customers': customers,
                'demands': demands_list,
                'connections': connections,
                'initial_demands': initial_demands
            }

        except Exception as e:
            print(f"Error loading data: {e}")
            raise

    @staticmethod
    def build_connections_map(connections_df: pd.DataFrame) -> Dict[Tuple[str, str], Connection]:
        """Build a map of all possible connections between nodes"""
        connections_map = {}

        try:
            for _, conn in connections_df.iterrows():
                connection = Connection(
                    id=conn['id'],
                    source_id=conn['from_id'],
                    destination_id=conn['to_id'],
                    transport_type=conn['connection_type'],
                    lead_time=int(conn['lead_time_days']),
                    max_capacity=float(conn['max_capacity']),
                    distance=float(conn['distance']),
                    cost_per_unit_distance=1.0,  # Default value
                    co2_per_unit_distance=0.5  # Default value
                )
                connections_map[(connection.source_id, connection.destination_id)] = connection

            print(f"Mapped {len(connections_map)} connections")

        except Exception as e:
            print(f"Error building connections map: {e}")
            print("Available columns:", connections_df.columns.tolist())

        return connections_map
