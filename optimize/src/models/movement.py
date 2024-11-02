from dataclasses import dataclass


@dataclass
class Movement:
    connection_id: str
    quantity: float
