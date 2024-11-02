from dataclasses import dataclass


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
