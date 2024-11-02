from dataclasses import dataclass


@dataclass
class Facility:
    id: str
    capacity: float
    current_level: float = 0.0

    def can_output(self, quantity: float) -> bool:
        return self.current_level >= quantity

    def can_input(self, quantity: float) -> bool:
        return self.current_level + quantity <= self.capacity
