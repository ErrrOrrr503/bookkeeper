"""
Budget restriction model
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from bookkeeper.repository.abstract_repository import AbstractRepository
from bookkeeper.models.category import Category
from bookkeeper.config import constants


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
    end : datetime
        End of budget period.
    budget_type : str
        Special budget type: daily, weekly, etc. Defined in constants.BUDGET_...
        For proper start and period recalculation.
        Types are added manually by developer.
        "" corresponds to common type - from user defined start to end.
    """

    cost_limit: int = 0
    start: datetime = datetime.now()
    end: datetime = datetime.now()
    budget_type: str = ''
    category: int | None = None
    pk: int = 0

    def __post_init__(self) -> None:
        self.recalculate_period()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return (self.cost_limit == other.cost_limit
                and self.end == other.end
                and self.start == other.start
                and self.budget_type == other.budget_type
                and self.category == other.category)

    def get_category(self, repo: AbstractRepository[Category]) -> Category | None:
        if self.category is None:
            return None
        return repo.get(self.category)

    def set_type(self, new_type: str) -> None:
        if new_type in [constants.BUDGET_DAILY,
                        constants.BUDGET_WEEKLY,
                        constants.BUDGET_MONTHLY]:
            self.budget_type = new_type
            self.recalculate_period()

    def recalculate_period(self) -> None:
        if self.budget_type == '':
            return
        dt_now = datetime.now()
        cur_day_start = datetime(dt_now.year, dt_now.month, dt_now.day)
        nxt_day_start = cur_day_start + timedelta(days=1)
        isoc_now = dt_now.isocalendar()
        cur_week_start = datetime.fromisocalendar(isoc_now.year, isoc_now.week, 1)
        nxt_week_start = cur_week_start + timedelta(weeks=1)
        cur_month_start = datetime(dt_now.year, dt_now.month, 1)
        nxt_month_start = (datetime(dt_now.year, dt_now.month + 1, 1)
                           if dt_now.month < 12 else
                           datetime(dt_now.year + 1, 1, 1))
        if self.budget_type == constants.BUDGET_DAILY:
            self.start = cur_day_start
            self.end = nxt_day_start
        elif self.budget_type == constants.BUDGET_WEEKLY:
            self.start = cur_week_start
            self.end = nxt_week_start
        elif self.budget_type == constants.BUDGET_MONTHLY:
            self.start = cur_month_start
            self.end = nxt_month_start
        else:
            raise NotImplementedError(f'Special budget type {self.budget_type} '
                                      'not implemented')
