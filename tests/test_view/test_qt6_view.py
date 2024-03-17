from bookkeeper.view.abstract_view import ExpenseEntry
from bookkeeper.view.qt6_view import ExpensesTableWidget

from datetime import datetime

import pytest
from pytestqt.qt_compat import qt_api

@pytest.fixture
def expenses_list():
    return [
        ExpenseEntry(str(datetime.now()), '666.13', 'Souls', 'soul purchase'),
        ExpenseEntry('01-01-1970', '146.00', 'Test', 'Test Comment')
    ]

def get_attr_allowed(attr_str):
    if attr_str == 'category':
        return ['Souls', 'Test', 'Drugs', 'Rock\'n\'Roll']
    return []

def test_hello(qtbot, expenses_list):
    widget = ExpensesTableWidget()
    widget.connect_get_expense_attr_allowed(get_attr_allowed)
    widget.set_contents(expenses_list)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.stop()
    #qtbot.mouseClick(
    #    widget.button_greet,
    #    qt_api.QtCore.Qt.MouseButton.LeftButton
    #)
    #assert widget.greet_label.text() == "Hello!"