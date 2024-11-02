from src.optimizer.supply_chain_optimizer import SupplyChainOptimizer

# Constants
API_KEY = "your-api-key"
BASE_URL = "http://localhost:8080/api/v1"
TOTAL_DAYS = 42


def main():
    optimizer = SupplyChainOptimizer(
        api_key=API_KEY,
        base_url=BASE_URL,
        total_days=TOTAL_DAYS
    )
    optimizer.run()


if __name__ == "__main__":
    main()
