"""
Budget restriction model
"""

from dataclasses import dataclass
from datetime import timedelta


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

    cost_limit: int
    category: int
    period: timedelta
    pk: int = 0
