# api/session_manager.py
from typing import Optional, Tuple, List, Dict

import requests

from src.models.demand import Demand


class SessionManager:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session_id = None
        self.headers = {
            'API-KEY': api_key,
            'Content-Type': 'application/json'
        }

    def start_session(self, max_retries: int = 3) -> bool:
        """Start a new game session with retry mechanism"""
        print("\nStarting new session...")

        # First try to cleanup any existing session
        if not self.cleanup_existing_session():
            print("Warning: Failed to clean up existing session")

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/session/start",
                    headers=self.headers
                )

                if response.status_code == 200:
                    self.session_id = response.text.strip()
                    if self.session_id:
                        print(f"Session started successfully. Session ID: {self.session_id}")
                        # Update headers with session ID
                        self.headers['SESSION-ID'] = self.session_id
                        return True
                else:
                    print(f"Failed to start session (Attempt {attempt + 1}/{max_retries})")
                    print(f"Status: {response.status_code}")
                    print(f"Response: {response.text}")

                if attempt < max_retries - 1:
                    print("Retrying in 2 seconds...")
                    import time
                    time.sleep(2)
            except Exception as e:
                print(f"Error starting session (Attempt {attempt + 1}/{max_retries}): {e}")

        return False

    def cleanup_existing_session(self) -> bool:
        """End any existing session"""
        print("\nAttempting to clean up existing session...")
        try:
            response = requests.post(
                f"{self.base_url}/session/end",
                headers=self.headers
            )
            return response.status_code in [200, 404]
        except Exception as e:
            print(f"Error cleaning up session: {e}")
            return False

    def make_move(self, current_day: int, movements: List[dict]) -> Optional[dict]:
        """Submit move for the current day"""
        if not self.session_id:
            print("No active session")
            return None

        try:
            data = {
                'day': current_day,
                'movements': movements
            }

            response = requests.post(
                f"{self.base_url}/play/round",
                headers=self.headers,
                json=data
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error making move: {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except Exception as e:
            print(f"Error making move: {e}")
            return None

    def process_round_result(self, result: dict) -> Tuple[List[Demand], List[dict], Dict, Dict]:
        """Process the result of a round"""
        if not result:
            return [], [], {}, {}

        # Process new demands
        new_demands = []
        for demand_data in result.get('demands', []):
            new_demands.append(Demand(
                id=demand_data['id'],
                customer_id=demand_data['customer_id'],
                quantity=demand_data['quantity'],
                post_day=demand_data['post_day'],
                start_delivery_day=demand_data['start_delivery_day'],
                end_delivery_day=demand_data['end_delivery_day']
            ))

        # Get penalties
        penalties = result.get('penalties', [])

        # Get KPIs
        delta_kpis = result.get('deltaKpis', {})
        total_kpis = result.get('totalKpis', {})

        return new_demands, penalties, delta_kpis, total_kpis
