from bookkeeper.view.abstract_view import ExpenseEntry, BudgetEntry
from bookkeeper.view.qt6_view import ExpensesTableWidget, BudgetTableWidget

from datetime import datetime

import pytest
from mock import Mock
from pytestqt.qt_compat import qt_api
from PySide6.QtCore import Qt

class TestExpenses:
    @pytest.fixture
    def expenses_list(self):
        return [
            ExpenseEntry(str(datetime.now()), '666.13', 'Souls', 'soul purchase'),
            ExpenseEntry('01-01-1970', '146.00', 'Tests', 'Test Comment')
        ]

    @staticmethod
    def get_attr_allowed(attr_str):
        if attr_str == 'category':
            return ['Souls', 'Tests', 'Drugs', 'Rock\'n\'Roll']
        return []

    def test_can_create(self, qtbot, expenses_list):
        expense_changed_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(self.get_attr_allowed)
        widget.connect_edited(expense_changed_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()

    def test_can_set_again(self, qtbot, expenses_list):
        """ setting contents must not generate editing events """
        expense_changed_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(self.get_attr_allowed)
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
        widget.connect_get_attr_allowed(self.get_attr_allowed)
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
        widget.connect_get_attr_allowed(self.get_attr_allowed)
        widget.connect_edited(expense_changed_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()
        widget.setCurrentCell(0, 2) # when gui editing this is automatically done by clicking.
        widget.cellWidget(0, 2).setCurrentIndex(3)
        e = expenses_list[0]
        e.category = 'Rock\'n\'Roll'
        expense_changed_callback.assert_called_with(0, e)

    def test_delete_entry(self, qtbot, expenses_list):
        expense_delete_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(self.get_attr_allowed)
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
        widget.connect_get_attr_allowed(self.get_attr_allowed)
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
        widget.connect_get_attr_allowed(self.get_attr_allowed)
        widget.connect_delete(expense_delete_callback)
        widget.connect_add(expense_add_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()
        #qtbot.stop()
        # TODO: autoclick
        #expense_add_callback.assert_called()

class TestBudgets:
    @pytest.fixture
    def budgets_list(self):
        return [
            BudgetEntry("Day", "146", "100", "All"),
            BudgetEntry("Week", "146", "100", "All"),
            BudgetEntry("Month", "146", "100", "Souls")
        ]

    @staticmethod
    def get_attr_allowed(attr_str):
        if attr_str == 'category':
            return [ 'All', 'Souls', 'Tests', 'Drugs', 'Rock\'n\'Roll']
        return []

    def test_can_create(self, qtbot, budgets_list):
        widget = BudgetTableWidget()
        widget.connect_get_attr_allowed(self.get_attr_allowed)
        widget.set_contents(budgets_list)
        qtbot.addWidget(widget)
        widget.show()
        #qtbot.stop()

class TestExpensesAdder():
    @staticmethod
    def get_attr_allowed(attr_str):
        if attr_str == 'category':
            return [ 'All', 'Souls', 'Tests', 'Drugs', 'Rock\'n\'Roll']
        return []

    @staticmethod
    def get_default_entry():
        return ExpenseEntry('1970-01-01', '0', 'All', 'comment')

    def test_can_create(self, qtbot):
        expense_add_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(self.get_attr_allowed)
        widget.connect_get_default_entry(self.get_default_entry)
        widget.connect_add(expense_add_callback)
        adder = widget.expenses_adder_widget()
        qtbot.addWidget(adder)
        adder.show()
        qtbot.stop()
        expense_add_callback.assert_called_once_with(self.get_default_entry())
