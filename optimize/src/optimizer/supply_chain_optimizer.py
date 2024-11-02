# optimizer/supply_chain_optimizer.py
from typing import Dict, List

from src.models.demand import Demand
from src.models.facility import Facility
from src.optimizer.advance_planner import AdvancedPlanner
from src.optimizer.data_loader import DataLoader
from src.optimizer.session_manager import SessionManager


class SupplyChainOptimizer:
    def __init__(self, api_key: str, base_url: str, total_days: int):
        self.api_key = api_key
        self.base_url = base_url
        self.total_days = total_days
        self.current_day = 0

        # Load initial data
        print("\nInitializing Supply Chain Optimizer...")
        self.data = DataLoader.load_data()

        # Initialize components
        self.facilities: Dict[str, Facility] = self.data['facilities']
        self.connections_map = self.data['connections_map']
        self.active_demands: List[Demand] = self.data['initial_demands']

        self.session_manager = SessionManager(api_key, base_url)
        self.movement_planner = AdvancedPlanner(
            facilities=self.facilities,
            connections_map=self.connections_map,
            valid_connections=self.data['valid_connections']
        )

        print("Initialization complete.")

    def run(self):
        """Run the complete supply chain optimization"""
        print("\nStarting Supply Chain Optimization")
        print("=================================")
        print(f"API URL: {self.base_url}")
        print(f"API Key: {self.api_key[:8]}...")
        print(f"Total Days: {self.total_days}")

        # Start session
        if not self.session_manager.start_session():
            print("Failed to start session. Exiting.")
            return

        try:
            # Main optimization loop
            while self.current_day < self.total_days:
                print(f"\nProcessing Day {self.current_day}")

                # Create movements for current day
                movements = self.movement_planner.create_movements(
                    self.current_day,
                    self.active_demands
                )

                # Submit movements and get results
                result = self.session_manager.make_move(self.current_day, movements)
                if not result:
                    print("Error occurred during move submission")
                    break

                # Process results and update state
                self._process_round_result(result)

                # Update facilities based on movements
                self._update_facility_levels(movements)

                # Clean up completed demands
                self._cleanup_completed_demands()

                # Print daily summary
                self._print_daily_summary(movements)

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

    def _process_round_result(self, result: dict) -> None:
        """Process round results and update state"""
        # Update day counter
        self.current_day += 1

        # Process new demands and penalties
        new_demands, penalties, delta_kpis, total_kpis = (
            self.session_manager.process_round_result(result)
        )

        # Add new demands to active demands
        self.active_demands.extend(new_demands)

        # Display round information
        self._display_round_info(
            new_demands_count=len(new_demands),
            penalties=penalties,
            delta_kpis=delta_kpis,
            total_kpis=total_kpis
        )

    def _update_facility_levels(self, movements: List[dict]) -> None:
        """Update facility levels based on movements"""
        for movement in movements:
            connection_id = movement['connection_id']
            quantity = movement['quantity']

            # Find corresponding connection
            connection = next(
                conn for conn in self.connections_map.values()
                if conn.id == connection_id
            )

            # Update source facility
            source = self.facilities[connection.source_id]
            source.current_level -= quantity

            # Update destination facility
            destination = self.facilities[connection.destination_id]
            destination.current_level += quantity

    def _cleanup_completed_demands(self) -> None:
        """Remove completed demands from active demands list"""
        self.active_demands = [
            demand for demand in self.active_demands
            if demand.remaining_quantity > 0 and
               demand.end_delivery_day >= self.current_day
        ]

    def _display_round_info(self, new_demands_count: int,
                            penalties: List[dict],
                            delta_kpis: Dict,
                            total_kpis: Dict) -> None:
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

    def _print_daily_summary(self, movements: List[dict]) -> None:
        """Print summary of daily operations"""
        if movements:
            print(f"\nSubmitted {len(movements)} movements")
            total_quantity = sum(m['quantity'] for m in movements)
            print(f"Total quantity moved: {total_quantity:.2f}")

            # Facility status
            print("\nFacility Status:")
            for facility in self.facilities.values():
                capacity_used = (facility.current_level / facility.capacity * 100)
                print(f"{facility.id}: {facility.current_level:.1f}/{facility.capacity:.1f} "
                      f"({capacity_used:.1f}% utilized)")
        else:
            print("No movements submitted for this day")
