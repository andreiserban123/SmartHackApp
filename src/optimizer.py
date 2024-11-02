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


class APITester:
    """Class for testing API connectivity and functionality"""

    def __init__(self):
        self.session_id = None
        self.headers = {"API-KEY": API_KEY, "Content-Type": "application/json"}

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

    def test_sample_move(self):
        """Test submitting a sample move"""
        print("\nTesting sample move submission...")
        if not self.session_id:
            print("✗ No active session")
            return False

        # Sample movement - you'll need to replace these IDs with actual ones from your data

        data = {
            "currentDay": 1,
            "movements": [
                {
                    "sourceId": "22911035-11f8-4557-8631-df09db9c1c1a",  # A refinery ID
                    "destinationId": "21b22968-9ef1-4568-bdd3-29d4488191ed",  # A storage tank ID
                    "amount": 100,
                }
            ],
        }

        try:
            response = requests.post(
                f"{BASE_URL}/moves", headers=self.headers, json=data
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")

            if response.status_code == 200:
                print("✓ Sample move submitted successfully")
                return True
            else:
                print("✗ Failed to submit sample move")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Error submitting move: {e}")
            return False

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

    # Test sample move
    tester.test_sample_move()

    # End session
    tester.test_end_session()


class SupplyChainData:
    """Class to load and manage supply chain data from CSV files"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.refineries = None
        self.storage_tanks = None
        self.customers = None
        self.costs = None
        self.emissions = None

    def load_data(self):
        """Load all CSV files from the data directory"""
        try:
            # Example CSV loading - adjust paths and column names based on your actual files
            self.refineries = pd.read_csv(os.path.join(self.data_dir, "refineries.csv"))
            self.storage_tanks = pd.read_csv(os.path.join(self.data_dir, "storage.csv"))
            self.customers = pd.read_csv(os.path.join(self.data_dir, "customers.csv"))
            self.costs = pd.read_csv(os.path.join(self.data_dir, "costs.csv"))
            self.emissions = pd.read_csv(os.path.join(self.data_dir, "emissions.csv"))
            return True
        except FileNotFoundError as e:
            print(f"Error loading data files: {e}")
            return False
        except pd.errors.EmptyDataError as e:
            print(f"Error: One of the CSV files is empty: {e}")
            return False


def main():
    print("Supply Chain Optimization API Tester")
    print("===================================")

    # Initialize data loader
    data = SupplyChainData("data")  # Assuming CSV files are in a 'data' subdirectory
    if data.load_data():
        print("Successfully loaded supply chain data")
        # Continue with optimization using data.refineries, data.storage_tanks etc.
    else:
        print("Failed to load supply chain data")
        return

    # Test API connectivity
    test_api_connectivity()


if __name__ == "__main__":
    main()
