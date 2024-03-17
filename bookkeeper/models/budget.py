"""
Budget restriction model
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any


@dataclass(slots=True)
class Budget:
    """

    Represents budget restriction.
    For specific category and time period.

    Attributes
    ----------
    pk : int
        id in repository (database).
    cost_limit : int
        Budget limit.
        Units are 0.01 of a currency unit - typical for USD/RUB.
    category : int
        id (or pk) of budget category - class Category instance.
    period : datetime
        Budget period.

    """

    cost_limit: int = 0
    period: timedelta = timedelta(seconds=0)
    category: int | None = None
    pk: int = 0

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.cost_limit == other.cost_limit
                and self.period == other.period
                and self.category == other.category)
