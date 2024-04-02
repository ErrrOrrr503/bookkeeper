"""
Expense operation representation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Expense:
    """
    Represents expense operation.

    Attributes
    ----------
    cost : int
        The cost of the operation.
        Units are 0.01 of a currency unit - typical for USD/RUB.
    category : int
        id (or pk) of expense category - class Category instance.
    expense_date : datetime
        When the operation was done.
    added_date : datetime
        When the operation was added in the database.
    comment : str
        Operation additional description or comment.
    pk : int
        id in repository (database).
    """

    cost: int = 0
    category: int | None = None
    expense_date: datetime = field(default_factory=datetime.now)
    added_date: datetime = field(default_factory=datetime.now)
    comment: str = ''
    pk: int = 0

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return (self.cost == other.cost
                and self.category == other.category
                and self.expense_date == other.expense_date
                and self.added_date == other.added_date
                and self.comment == other.comment)
