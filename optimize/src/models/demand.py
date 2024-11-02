# models/demand.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class Demand:
    id: str
    customer_id: str
    quantity: float
    post_day: int
    start_delivery_day: int
    end_delivery_day: int
    remaining_quantity: Optional[float] = None

    def __post_init__(self):
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
