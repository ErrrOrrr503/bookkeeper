from bookkeeper.view.abstract_view import AbstractExpenses, ExpenseEntry
from typing import Callable

import pytest

def test_expenses_cannot_create_abstract():
    with pytest.raises(TypeError):
        AbstractExpenses()


def test_expenses_can_create_subclass():
    class Test(AbstractExpenses):
        def set_contents(self, entries: list[ExpenseEntry]) -> None: pass
        def set_at_position(self, position: int, entry: ExpenseEntry) -> None: pass
        def connect_expense_edited(self, callback: Callable[[int, ExpenseEntry], None]) -> None: pass
        def connect_get_expense_attr_allowed(self, callback: Callable[[str], list[str]]) -> None: pass

    t = Test()
    assert isinstance(t, AbstractExpenses)

def test_expenses_cant_create_subclass_without_overriding():
    class Test(AbstractExpenses):
        def set_at_position(self, position: int, entry: ExpenseEntry) -> None: pass
        def connect_expense_edited(self, callback: Callable[[int, ExpenseEntry], None]) -> None: pass
        def connect_get_expense_attr_allowed(self, callback: Callable[[str], list[str]]) -> None: pass

    with pytest.raises(TypeError):
        t = Test()
