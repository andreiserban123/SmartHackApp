# Supply Chain Optimization Application for SmartHacks 2024
# This application optimizes fuel delivery from refineries to customers through storage tanks
# while minimizing costs and CO2 emissions.

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import requests
import json
import sys
import os
from datetime import datetime, timedelta

# Constants
API_KEY = "7bcd6334-bc2e-4cbf-b9d4-61cb9e868869"
BASE_URL = "http://localhost:8080/api/v1"
TOTAL_DAYS = 42  # Configurable number of rounds


class SupplyChainData:
    """Class to load and manage supply chain data from CSV files"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.refineries_df = None
        self.tanks_df = None
        self.customers_df = None
        self.demands_df = None

    def load_data(self):
        """Load all CSV files from the data directory"""
        try:
            print(f"\nLoading data from {self.data_dir}")

            # Load data with semicolon separator
            self.refineries_df = pd.read_csv(
                os.path.join(self.data_dir, "refineries.csv"), sep=";"
            )
            self.tanks_df = pd.read_csv(
                os.path.join(self.data_dir, "tanks.csv"), sep=";"
            )
            self.customers_df = pd.read_csv(
                os.path.join(self.data_dir, "customers.csv"), sep=";"
            )
            self.demands_df = pd.read_csv(
                os.path.join(self.data_dir, "demands.csv"), sep=";"
            )

            print("\nData loaded successfully:")
            print(f"Refineries: {len(self.refineries_df)} records")
            print(f"Storage Tanks: {len(self.tanks_df)} records")
            print(f"Customers: {len(self.customers_df)} records")
            print(f"Demands: {len(self.demands_df)} records")
            return True

        except FileNotFoundError as e:
            print(f"Error loading data files: {e}")
            return False
        except pd.errors.EmptyDataError as e:
            print(f"Error: One of the CSV files is empty: {e}")
            return False

    def get_refinery_info(self, refinery_id: str) -> dict:
        """Get information about a specific refinery"""
        refinery = self.refineries_df[self.refineries_df["id"] == refinery_id].iloc[0]
        return refinery.to_dict()

    def get_tank_info(self, tank_id: str) -> dict:
        """Get information about a specific storage tank"""
        tank = self.tanks_df[self.tanks_df["id"] == tank_id].iloc[0]
        return tank.to_dict()

    def get_customer_info(self, customer_id: str) -> dict:
        """Get information about a specific customer"""
        customer = self.customers_df[self.customers_df["id"] == customer_id].iloc[0]
        return customer.to_dict()

    def get_customer_demands(self, customer_id: str) -> pd.DataFrame:
        """Get all demands for a specific customer"""
        return self.demands_df[self.demands_df["customer_id"] == customer_id]


class APITester:
    """Class for testing API connectivity and functionality"""

    def __init__(self):
        self.session_id = None
        self.headers = {"API-KEY": API_KEY, "Content-Type": "application/json"}
        self.data = SupplyChainData()
        self.data.load_data()

    def test_start_session(self):
        """Test starting a new session"""
        print("\nTesting session start...")
        try:
            response = requests.post(f"{BASE_URL}/session/start", headers=self.headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")

            if response.status_code == 200:
                self.session_id = response.json()["sessionId"]
                self.headers["SESSION-ID"] = self.session_id
                print("✓ Session started successfully")
                return True
            else:
                print("✗ Failed to start session")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Error connecting to API: {e}")
            return False

    def test_empty_move(self):
        """Test submitting an empty move"""
        print("\nTesting empty move submission...")
        if not self.session_id:
            print("✗ No active session")
            return False

        data = {"currentDay": 0, "movements": []}

        try:
            response = requests.post(
                f"{BASE_URL}/moves", headers=self.headers, json=data
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")

            if response.status_code == 200:
                print("✓ Empty move submitted successfully")
                return True
            else:
                print("✗ Failed to submit move")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Error submitting move: {e}")
            return False

    def create_test_movements(self, day: int) -> dict:
        """Create test movements based on the day"""
        movements = []

        # Get some sample IDs
        refinery_id = self.data.refineries_df["id"].iloc[0]  # First refinery
        tank_id = self.data.tanks_df["id"].iloc[0]  # First storage tank
        customer_id = self.data.customers_df["id"].iloc[0]  # First customer

        # Day 1: Refinery to Storage Tank movements
        if day == 1:
            movements = [
                {
                    "sourceId": refinery_id,
                    "destinationId": tank_id,
                    "amount": float(
                        min(
                            self.data.get_refinery_info(refinery_id)["max_output"],
                            self.data.get_tank_info(tank_id)["max_input"],
                        )
                        / 2
                    ),  # Using half of the smaller maximum capacity
                }
            ]
            print(f"\nMoving from Refinery {refinery_id} to Tank {tank_id}")
            print(
                f"Refinery max output: {self.data.get_refinery_info(refinery_id)['max_output']}"
            )
            print(f"Tank max input: {self.data.get_tank_info(tank_id)['max_input']}")

        # Day 2: Storage Tank to Customer movements
        elif day == 2:
            customer_demand = self.data.get_customer_demands(customer_id)
            if not customer_demand.empty:
                demand_amount = customer_demand.iloc[0]["quantity"]
                movements = [
                    {
                        "sourceId": tank_id,
                        "destinationId": customer_id,
                        "amount": float(
                            min(
                                demand_amount,
                                self.data.get_customer_info(customer_id)["max_input"],
                                self.data.get_tank_info(tank_id)["max_output"],
                            )
                        ),
                    }
                ]
                print(f"\nMoving from Tank {tank_id} to Customer {customer_id}")
                print(f"Demand amount: {demand_amount}")
                print(
                    f"Customer max input: {self.data.get_customer_info(customer_id)['max_input']}"
                )
                print(
                    f"Tank max output: {self.data.get_tank_info(tank_id)['max_output']}"
                )

        return {"currentDay": day, "movements": movements}

    def test_sample_moves(self):
        """Test submitting sample moves for multiple days"""
        if not self.session_id:
            print("✗ No active session")
            return False

        for day in range(1, 3):
            print(f"\nTesting moves for day {day}...")
            data = self.create_test_movements(day)

            print(f"\nRequest payload:")
            print(json.dumps(data, indent=2))

            try:
                response = requests.post(
                    f"{BASE_URL}/moves", headers=self.headers, json=data
                )
                print(f"Status Code: {response.status_code}")
                print(f"Response: {json.dumps(response.json(), indent=2)}")

                if response.status_code == 200:
                    print(f"✓ Day {day} moves submitted successfully")
                else:
                    print(f"✗ Failed to submit moves for day {day}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"✗ Error submitting moves: {e}")
                return False
        return True

    def test_end_session(self):
        """Test ending the session"""
        print("\nTesting session end...")
        try:
            response = requests.post(f"{BASE_URL}/session/end", headers=self.headers)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                print("✓ Session ended successfully")
                return True
            else:
                print("✗ Failed to end session")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Error ending session: {e}")
            return False


def test_api_connectivity():
    """Run all API tests"""
    tester = APITester()

    # Start session
    if not tester.test_start_session():
        return

    # Test empty move
    tester.test_empty_move()

    # Test sample moves
    tester.test_sample_moves()

    # End session
    tester.test_end_session()


def main():
    print("Supply Chain Optimization API Tester")
    print("===================================")
    print(f"API URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:8]}...")

    # Test API connectivity
    test_api_connectivity()


if __name__ == "__main__":
    main()
