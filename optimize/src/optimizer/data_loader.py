from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.models.connection import Connection
from src.models.demand import Demand
from src.models.facility import Facility


class DataLoader:
    @staticmethod
    def load_data(possible_paths: Optional[List[Path]] = None) -> dict:
        """Load and prepare all necessary data"""
        if possible_paths is None:
            possible_paths = [
                Path("data"),
                Path("../data"),
                Path("../../data"),
            ]

        data_dir = next((path for path in possible_paths if path.exists()), None)
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

            # Create validated connection lookup
            valid_connections = DataLoader._create_connection_lookup(connections)

            # Create facility objects
            facilities = DataLoader._create_facilities(refineries, tanks, customers)

            # Create connection objects
            connections_map = DataLoader._create_connections_map(connections)

            # Process demands
            demands_list = DataLoader._process_demands(demands, valid_connections)
            initial_demands = [d for d in demands_list if d.post_day == 0]

            print(f"Loaded: {len(refineries)} refineries, {len(tanks)} tanks, "
                  f"{len(customers)} customers, {len(demands_list)} demands, "
                  f"{len(connections)} connections")

            return {
                'facilities': facilities,
                'demands': demands_list,
                'initial_demands': initial_demands,
                'connections_map': connections_map,
                'valid_connections': valid_connections
            }

        except Exception as e:
            print(f"Error loading data: {e}")
            raise

    @staticmethod
    def _create_facilities(refineries: pd.DataFrame, tanks: pd.DataFrame,
                           customers: pd.DataFrame) -> Dict[str, Facility]:
        """Create facility objects from dataframes"""
        facilities = {}

        # Add refineries
        for _, row in refineries.iterrows():
            facilities[row['id']] = Facility(
                id=row['id'],
                capacity=float(row['capacity']),
                current_level=float(row['initial_stock'])
            )

        # Add tanks
        for _, row in tanks.iterrows():
            facilities[row['id']] = Facility(
                id=row['id'],
                capacity=float(row['capacity']),
                current_level=float(row['initial_stock'])
            )

        # Add customers
        for _, row in customers.iterrows():
            facilities[row['id']] = Facility(
                id=row['id'],
                capacity=float(row['max_input']),
                current_level=0.0  # Customers start empty
            )

        return facilities

    @staticmethod
    def _create_connection_lookup(connections: pd.DataFrame) -> Dict[str, Dict[str, str]]:
        """Create a lookup dictionary for valid connections with their IDs"""
        valid_connections = {}

        for _, conn in connections.iterrows():
            source_id = conn['from_id']
            dest_id = conn['to_id']
            conn_id = conn['id']

            if source_id not in valid_connections:
                valid_connections[source_id] = {}

            valid_connections[source_id][dest_id] = conn_id

        return valid_connections

    @staticmethod
    def _create_connections_map(connections: pd.DataFrame) -> Dict[Tuple[str, str], Connection]:
        """Build a map of all possible connections between nodes"""
        connections_map = {}

        for _, conn in connections.iterrows():
            connection = Connection(
                id=conn['id'],
                source_id=conn['from_id'],
                destination_id=conn['to_id'],
                transport_type=conn['connection_type'],
                lead_time=int(conn['lead_time_days']),
                max_capacity=float(conn['max_capacity']),
                distance=float(conn['distance'])
            )
            connections_map[(connection.source_id, connection.destination_id)] = connection

        return connections_map

    @staticmethod
    def _process_demands(demands: pd.DataFrame,
                         valid_connections: Dict[str, Dict[str, str]]) -> List[Demand]:
        """Process demands and validate connections"""
        demands_list = []

        def has_valid_connection(customer_id: str) -> bool:
            return any(customer_id in destinations
                       for destinations in valid_connections.values())

        for _, row in demands.iterrows():
            if has_valid_connection(row['customer_id']):
                demand = Demand(
                    id=row['id'],
                    customer_id=row['customer_id'],
                    quantity=row['quantity'],
                    post_day=row['post_day'],
                    start_delivery_day=row['start_delivery_day'],
                    end_delivery_day=row['end_delivery_day']
                )
                demands_list.append(demand)

        return demands_list
