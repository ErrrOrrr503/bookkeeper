"""
View types and abstract class
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Protocol, Any, Callable
from dataclasses import dataclass


# TODO: translation
@dataclass
class ExpenseEntry:
    """
    Type that represents ExpensesTable row.

    Default attributes represent column names.
    All attributes are strings. View's job is not to format, but to draw.
    """
    date: str = 'Date'
    cost: str = 'Cost'
    category: str = 'Category'
    comment: str = 'Comment'

class AbstractExpenses(ABC):
    """
    Abstract expenses list viewer, i.e. table widget
    """
    @abstractmethod
    def set_contents(self, entries: list[ExpenseEntry]) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_at_position(self, position: int, entry: ExpenseEntry) -> None:
        raise NotImplementedError

    @abstractmethod
    def connect_expense_edited(self, callback: Callable[[int, ExpenseEntry], None]):
        raise NotImplementedError

    @abstractmethod
    def connect_get_expense_attr_allowed(self, callback: Callable[[str], list[str]]):
        raise NotImplementedError

