from bookkeeper.view.abstract_view import ExpenseEntry
from bookkeeper.view.qt6_view import ExpensesTableWidget

from datetime import datetime

import pytest
from mock import Mock
from pytestqt.qt_compat import qt_api

@pytest.fixture
def expenses_list():
    return [
        ExpenseEntry(str(datetime.now()), '666.13', 'Souls', 'soul purchase'),
        ExpenseEntry('01-01-1970', '146.00', 'Tests', 'Test Comment')
    ]

def get_attr_allowed(attr_str):
    if attr_str == 'category':
        return ['Souls', 'Tests', 'Drugs', 'Rock\'n\'Roll']
    return []

def test_can_create(qtbot, expenses_list):
    expense_changed_callback = Mock()
    widget = ExpensesTableWidget()
    widget.connect_get_expense_attr_allowed(get_attr_allowed)
    widget.connect_expense_edited(expense_changed_callback)
    widget.set_contents(expenses_list)
    qtbot.addWidget(widget)
    widget.show()

def test_can_set_again(qtbot, expenses_list):
    """ setting contents must not generate editing events """
    expense_changed_callback = Mock()
    widget = ExpensesTableWidget()
    widget.connect_get_expense_attr_allowed(get_attr_allowed)
    widget.connect_expense_edited(expense_changed_callback)
    widget.set_contents(expenses_list)
    expense_changed_callback.assert_not_called()
    qtbot.addWidget(widget)
    widget.show()
    widget.set_contents(expenses_list)
    expense_changed_callback.assert_not_called()

def test_edit_item(qtbot, expenses_list):
    expense_changed_callback = Mock()
    widget = ExpensesTableWidget()
    widget.connect_get_expense_attr_allowed(get_attr_allowed)
    widget.connect_expense_edited(expense_changed_callback)
    widget.set_contents(expenses_list)
    qtbot.addWidget(widget)
    widget.show()
    widget.item(0, 0).setText("DATE")
    e = expenses_list[0]
    e.date = "DATE"
    expense_changed_callback.assert_called_with(0, e)

def test_edit_qbox(qtbot, expenses_list):
    expense_changed_callback = Mock()
    widget = ExpensesTableWidget()
    widget.connect_get_expense_attr_allowed(get_attr_allowed)
    widget.connect_expense_edited(expense_changed_callback)
    widget.set_contents(expenses_list)
    qtbot.addWidget(widget)
    widget.show()
    widget.setCurrentCell(0, 2) # when gui editing this is automatically done by clicking.
    widget.cellWidget(0, 2).setCurrentIndex(3)
    e = expenses_list[0]
    e.category = 'Rock\'n\'Roll'
    expense_changed_callback.assert_called_with(0, e)