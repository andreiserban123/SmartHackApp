from typing import Optional, Tuple

import requests

from src.models.demand import Demand


class SessionManager:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session_id = None

    def start_session(self) -> bool:
        """Start a new game session"""
        print("\nStarting new session...")

        if not self.cleanup_existing_session():
            print("Warning: Failed to clean up existing session")

        headers = {
            'API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            print("Sending session start request...")
            response = requests.post(f"{self.base_url}/session/start", headers=headers)

            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")

            if response.status_code == 200:
                self.session_id = response.text.strip()
                if self.session_id:
                    print(f"Session started successfully. Session ID: {self.session_id}")
                    return True

            return False

        except Exception as e:
            print(f"Error starting session: {e}")
            return False

    def cleanup_existing_session(self) -> bool:
        """End any existing session"""
        print("\nAttempting to clean up existing session...")

        headers = {
            'API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(f"{self.base_url}/session/end", headers=headers)
            print(f"Cleanup response status: {response.status_code}")

            if response.status_code in [200, 404]:
                print("Session cleanup successful")
                return True
            else:
                print(f"Failed to clean up session: {response.status_code}")
                return False

        except Exception as e:
            print(f"Error cleaning up session: {e}")
            return False

    def make_move(self, current_day: int, movements: list) -> Optional[dict]:
        """Submit move for the current day"""
        if not self.session_id:
            print("No active session")
            return None

        headers = {
            'API-KEY': self.api_key,
            'SESSION-ID': self.session_id,
            'Content-Type': 'application/json'
        }

        data = {
            'day': current_day,
            'movements': movements
        }

        try:
            response = requests.post(f"{self.base_url}/play/round", headers=headers, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error making move: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error making move: {e}")
            return None

    def process_round_result(self, result: dict) -> Tuple[list, dict, dict]:
        """Process the result of a round"""
        # Process new demands
        new_demands = []
        for demand_data in result.get('demands', []):
            new_demands.append(Demand(**demand_data))

        # Process penalties
        penalties = result.get('penalties', [])

        # Get KPIs
        delta_kpis = result.get('deltaKpis', {})
        total_kpis = result.get('totalKpis', {})

        return new_demands, penalties, delta_kpis, total_kpis
