from bookkeeper.view.abstract_view import ExpenseEntry, BudgetEntry, CategoryEntry
from bookkeeper.view.qt6_view import ExpensesTableWidget, BudgetTableWidget, CategoriesWidget, Qt6View
from bookkeeper.utils import read_tree

from datetime import datetime

import pytest
from mock import Mock
from pytestqt.qt_compat import qt_api
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

@pytest.fixture
def expenses_list():
    return [
        ExpenseEntry(str(datetime.now()), '666.13', 'Souls', 'soul purchase'),
        ExpenseEntry('01-01-1970', '146.00', 'Tests', 'Test Comment')
    ]

@pytest.fixture
def budgets_list():
    return [
        BudgetEntry("Day", "146", "100", "-"),
        BudgetEntry("Week", "146", "100", "-"),
        BudgetEntry("Month", "146", "100", "Souls")
    ]

@pytest.fixture
def categories_sorted_list():
    cats = """
foodstuff
    meat
        raw meat
        meat products
    candies
books
clothing
        """.splitlines()
    entries = [ CategoryEntry(t[0], t[1] if t[1] is not None else '-') for t in read_tree(cats) ]
    return entries

def get_attr_allowed(attr_str):
    if attr_str == 'category':
        return [ '-', 'Souls', 'Tests', 'Drugs', 'Rock\'n\'Roll']
    return []

def get_default_category():
    return CategoryEntry('new category', '-')


def get_default_expense():
    return ExpenseEntry('1970-01-01', '0', '-', 'comment')


class TestExpenses:

    def test_can_create(self, qtbot, expenses_list):
        expense_changed_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_edited(expense_changed_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()

    def test_can_set_again(self, qtbot, expenses_list):
        """ setting contents must not generate editing events """
        expense_changed_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_edited(expense_changed_callback)
        widget.set_contents(expenses_list)
        expense_changed_callback.assert_not_called()
        qtbot.addWidget(widget)
        widget.show()
        widget.set_contents(expenses_list)
        expense_changed_callback.assert_not_called()

    def test_edit_item(self, qtbot, expenses_list):
        expense_changed_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_edited(expense_changed_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()
        widget.item(0, 0).setText("DATE")
        e = expenses_list[0]
        e.date = "DATE"
        expense_changed_callback.assert_called_with(0, e)

    def test_edit_qbox(self, qtbot, expenses_list):
        expense_changed_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_edited(expense_changed_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()
        widget.setCurrentCell(1, 2) # when gui editing this is automatically done by clicking.
        widget.cellWidget(1, 2).setCurrentIndex(4)
        e = expenses_list[1]
        e.category = get_attr_allowed('category')[4]
        expense_changed_callback.assert_called_with(1, e)

    def test_delete_entry(self, qtbot, expenses_list):
        expense_delete_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_delete(expense_delete_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()
        widget.setCurrentCell(0, 0)
        qtbot.keyClick(widget, Qt.Key_Delete)
        expense_delete_callback.assert_called_with([0])

    def test_context_delete_entry(self, qtbot, expenses_list):
        expense_delete_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_delete(expense_delete_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()
        #qtbot.stop()
        widget.setCurrentCell(0, 0)
        qtbot.keyClick(widget, Qt.Key_Delete)
        expense_delete_callback.assert_called_with([0])

    def test_context_add_entry(self, qtbot, expenses_list):
        expense_delete_callback = Mock()
        expense_add_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_delete(expense_delete_callback)
        widget.connect_add(expense_add_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()
        #qtbot.stop()
        # TODO: autoclick
        #expense_add_callback.assert_called()

class TestBudgets:

    def test_can_create(self, qtbot, budgets_list):
        widget = BudgetTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.set_contents(budgets_list)
        qtbot.addWidget(widget)
        #widget.show()

class TestExpensesAdder:

    def test_can_add(self, qtbot):
        expense_add_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_get_default_entry(get_default_expense)
        widget.connect_add(expense_add_callback)
        adder = widget.expenses_adder_widget()
        qtbot.addWidget(adder)
        adder.show()
        qtbot.mouseClick(
            adder.add_button_widget,
            qt_api.QtCore.Qt.MouseButton.LeftButton
        )
        expense_add_callback.assert_called_once_with(get_default_expense())


class TestCategoriesWidget:

    def test_can_add(self, qtbot, categories_sorted_list):
        category_add_callback = Mock()
        widget = CategoriesWidget()
        widget.set_contents(categories_sorted_list)
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_get_default_entry(get_default_category)
        widget.connect_add(category_add_callback)
        qtbot.addWidget(widget)
        widget.show()
        qtbot.mouseClick(
            widget.adder.add_button_widget,
            qt_api.QtCore.Qt.MouseButton.LeftButton
        )
        category_add_callback.assert_called_once_with(get_default_category())


class TestQt6View:

    def test_can_create(self, qtbot, expenses_list, budgets_list):
        view = Qt6View()
        view.expenses.connect_get_attr_allowed(get_attr_allowed)
        view.expenses.set_contents(expenses_list)
        view.budgets.connect_get_attr_allowed(get_attr_allowed)
        view.budgets.set_contents(budgets_list)
        view.expenses.connect_get_default_entry(get_default_expense)
        view.window.show()
        qtbot.stop()