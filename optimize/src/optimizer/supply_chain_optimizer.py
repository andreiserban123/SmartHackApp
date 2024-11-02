import time

from src.optimizer.data_loader import DataLoader
from src.optimizer.movement_creator import MovementCreator
from src.optimizer.session_manager import SessionManager


class SupplyChainOptimizer:
    def __init__(self, api_key: str, base_url: str, total_days: int):
        self.api_key = api_key
        self.base_url = base_url
        self.total_days = total_days
        self.current_day = 0

        # Load data
        self.data = DataLoader.load_data()
        self.connections_map = DataLoader.build_connections_map(self.data['connections'])
        self.active_demands = self.data['initial_demands']

        # Initialize components
        self.session_manager = SessionManager(api_key, base_url)
        self.movement_creator = MovementCreator(self.data, self.connections_map)

    def _start_session_with_retry(self, max_retries: int = 3) -> bool:
        """Start a new session with retry mechanism"""
        for attempt in range(max_retries):
            if self.session_manager.start_session():
                return True
            else:
                if attempt < max_retries - 1:
                    print(f"Retrying session start ({attempt + 2}/{max_retries})...")
                    time.sleep(2)  # Wait 2 seconds before retry
                else:
                    print("Failed to start session after all retries")
                    return False
        return False

    def _process_round_result(self, result: dict):
        """Process the result of a round and update state"""
        if not result:
            return False

        # Update day
        self.current_day += 1

        # Process new demands and update active demands
        new_demands, penalties, delta_kpis, total_kpis = self.session_manager.process_round_result(result)
        self.active_demands.extend(new_demands)

        # Display round information
        self._display_round_info(len(new_demands), penalties, delta_kpis, total_kpis)

        return True

    def _display_round_info(self, new_demands_count: int, penalties: list, delta_kpis: dict, total_kpis: dict):
        """Display information about the current round"""
        print(f"\nDay {self.current_day} Summary:")
        print(f"New demands received: {new_demands_count}")
        print(f"Total active demands: {len(self.active_demands)}")

        # Display penalties if any
        if penalties:
            print("\nPenalties:")
            penalty_types = {}
            for penalty in penalties:
                ptype = penalty['type']
                if ptype not in penalty_types:
                    penalty_types[ptype] = {'count': 0, 'cost': 0, 'co2': 0}
                penalty_types[ptype]['count'] += 1
                penalty_types[ptype]['cost'] += penalty['cost']
                penalty_types[ptype]['co2'] += penalty['co2']

            for ptype, stats in penalty_types.items():
                print(f"{ptype}: {stats['count']} occurrences, "
                      f"Cost: {stats['cost']:.2f}, CO2: {stats['co2']:.2f}")

        # Display KPIs
        print("\nKPIs:")
        print(f"Delta - Cost: {delta_kpis.get('cost', 0):.2f}, "
              f"CO2: {delta_kpis.get('co2', 0):.2f}")
        print(f"Total - Cost: {total_kpis.get('cost', 0):.2f}, "
              f"CO2: {total_kpis.get('co2', 0):.2f}")

    def run(self):
        """Run the complete optimization"""
        print("\nStarting Supply Chain Optimization")
        print("=================================")
        print(f"API URL: {self.base_url}")
        print(f"API Key: {self.api_key[:8]}...")

        # Start session with retry
        if not self._start_session_with_retry():
            return

        # Run optimization
        try:
            while self.current_day < self.total_days:
                print(f"\nProcessing day {self.current_day}")

                # Create and submit movements
                movements = self.movement_creator.create_movements(
                    self.current_day, self.active_demands)

                # Submit movements and process results
                result = self.session_manager.make_move(self.current_day, movements)

                # Process round result and update state
                if not self._process_round_result(result):
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
            import traceback
            traceback.print_exc()
        finally:
            # Always try to end session cleanly
            if self.session_manager.session_id:
                self.session_manager.cleanup_existing_session()
