"""
Budget restriction model
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from bookkeeper.repository.abstract_repository import AbstractRepository
from bookkeeper.models.category import Category

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
    start : datetime
        Start of budget period.
    period : timedelta
        Budget period.
    budget_type : str
        Special budget type: daily, weekly, etc.
        For proper start and period recalculation.
    """

    cost_limit: int = 0
    start: datetime = datetime.now()
    period: timedelta = timedelta(seconds=0)
    budget_type: str = ""
    category: int | None = None
    pk: int = 0

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.cost_limit == other.cost_limit
                and self.period == other.period
                and self.start == other.start
                and self.description == other.description
                and self.category == other.category)

    def get_category(self, repo: AbstractRepository[Category]) -> Category | None:
        if self.category is None:
            return None
        return repo.get(self.category)
