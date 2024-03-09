"""
Expense operation representation
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Expense:
    """
    Represents expense operation.

    Attributes
    ----------
    cost : float
        The cost of the operation.
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

    cost: float
    category: int
    expense_date: datetime = field(default_factory=datetime.now)
    added_date: datetime = field(default_factory=datetime.now)
    comment: str = ''
    pk: int = 0
