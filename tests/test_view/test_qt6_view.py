from bookkeeper.view.abstract_view import ExpenseEntry, BudgetEntry, CategoryEntry, ViewError, ViewWarning
from bookkeeper.view.qt6_view import ExpensesTableWidget, BudgetTableWidget, CategoriesWidget, Qt6View, call_callback, partial_none, SelfUpdatableCombo
from bookkeeper.utils import read_tree
from bookkeeper.config import constants

from datetime import datetime
from functools import partial

import pytest
from mock import Mock
from pytestqt.qt_compat import qt_api
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QMessageBox

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

class TestMisc:

    def test_call_callback(self, qtbot):
        callback = Mock(return_value=None)
        widget = QWidget()
        assert call_callback(widget, None) == (None, 'NoneCallback')
        assert call_callback(widget, callback, 1, b=2) == (None, None)
        callback.assert_called_once_with(1, b=2)

    def test_call_callback_err(self, qtbot, monkeypatch):

        def callback_warn():
            raise ViewWarning('Warning')

        def callback_err():
            raise ViewError('Error')

        def callback_fatal():
            raise Exception('Fatal')

        monkeypatch.setattr(QMessageBox, 'critical', lambda *args: QMessageBox.Yes)
        monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.Yes)

        widget = QWidget()

        assert call_callback(widget, callback_warn) == (None, 'Warning')
        assert call_callback(widget, callback_err) == (None, 'Error')
        assert call_callback(widget, callback_fatal) == (None, 'Fatal')

    def test_partial_none(self):
        f = Mock(return_value=None)
        assert partial_none(None) == None
        p = partial_none(f, 1, b=2)
        p(c=3)
        f.assert_called_once_with(1, b=2, c=3)

class TestSetfUpdatableCombo:
    """
    Unfortunately, qtbot clicking does not generate paintEvent.
    And it seems, qtbot can't fake Wheel.
    """
    def entries_1(self):
        return ['1', '2', '3']

    def entries_2(self):
        return ['4', '5', '6']

    def test_can_create(self):
        c = SelfUpdatableCombo(self.entries_1)
        c.show()

    def test_text_changed_callbacks(self, qtbot):
        c = SelfUpdatableCombo(self.entries_1)
        cb = Mock()
        c.connect_text_changed(cb)
        assert c._receivers == [ cb ]
        c.disconnect_text_changed(cb)
        assert c._receivers == []
        c.connect_text_changed(cb)
        c.set_content('3')
        cb.assert_called_once_with('3')
        c.get_contents = self.entries_2
        c.update_contents()
        cb.assert_called_once_with('3')  # no extra calls
        assert c._receivers == [ cb ]


class TestExpenses:

    def test_can_create(self, qtbot, expenses_list):
        expense_changed_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_edited(expense_changed_callback)
        widget.set_contents(expenses_list)
        qtbot.addWidget(widget)
        widget.show()

    def test_bad_attr_allowed(self, qtbot, expenses_list, monkeypatch):

        def bad_attr_allowed(*args, **kwargs):
            raise ViewError

        monkeypatch.setattr(QMessageBox, 'critical', lambda *args: QMessageBox.Yes)
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(bad_attr_allowed)
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
        widget.setCurrentCell(0, 0)
        del_action = widget._context_menu.actions()[0]
        del_action.trigger()
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
        add_action = widget._context_menu.actions()[1]
        add_action.trigger()
        expense_add_callback.assert_called_with(ExpenseEntry())
        widget.connect_get_default_entry(get_default_expense)
        add_action.trigger()
        expense_add_callback.assert_called_with(get_default_expense())


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

    def test_can_edit_categories(self, qtbot):
        expense_add_callback = Mock()
        categories_edit_callback = Mock()
        widget = ExpensesTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_get_default_entry(get_default_expense)
        widget.connect_add(expense_add_callback)
        widget.connect_edit_categories(categories_edit_callback)
        adder = widget.expenses_adder_widget()
        qtbot.addWidget(adder)
        adder.show()
        qtbot.mouseClick(
            adder.edit_cat_button_widget,
            qt_api.QtCore.Qt.MouseButton.LeftButton
        )
        categories_edit_callback.assert_called_once()


class TestBudgets:

    def test_can_create(self, qtbot, budgets_list):
        widget = BudgetTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.set_contents(budgets_list)
        qtbot.addWidget(widget)
        widget.show()

    def test_color(self, qtbot, budgets_list):
        widget = BudgetTableWidget()
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.set_contents(budgets_list)
        widget.color_entry(0, 127, 0, 0)
        widget.color_entry(1, 127, 127, 0)
        qtbot.addWidget(widget)
        widget.show()


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

    def test_can_delete(self, qtbot, categories_sorted_list):
        category_delete_callback = Mock()
        widget = CategoriesWidget()
        widget.set_contents(categories_sorted_list)
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_get_default_entry(get_default_category)
        widget.connect_delete(category_delete_callback)
        qtbot.addWidget(widget)
        widget.show()
        widget.tree.setCurrentItem(widget.tree.itemAt(0, 0))
        qtbot.keyClick(widget, Qt.Key_Delete)
        category_delete_callback.assert_called_with([0])

    def test_edit(self, qtbot, categories_sorted_list):
        category_edited_callback = Mock()
        widget = CategoriesWidget()
        widget.set_contents(categories_sorted_list)
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_get_default_entry(get_default_category)
        widget.connect_edited(category_edited_callback)
        qtbot.addWidget(widget)
        widget.show()
        widget.tree.itemAt(0, 0).setText(0, 'edit')
        category_edited_callback.assert_called_once_with(0, CategoryEntry('edit', constants.TOP_CATEGORY_NAME))

    def test_set_at_position(self, qtbot, categories_sorted_list):
        widget = CategoriesWidget()
        widget.set_contents(categories_sorted_list)
        widget.connect_get_attr_allowed(get_attr_allowed)
        widget.connect_get_default_entry(get_default_category)
        qtbot.addWidget(widget)
        widget.show()
        widget.set_at_position(0, CategoryEntry('setpos', '-'))
        assert widget.tree.itemAt(0, 0).text(0) == 'setpos'
        with pytest.raises(ValueError):
            widget.set_at_position(146, CategoryEntry('setpos', '-'))


class TestQt6View:

    @staticmethod
    def monkey_create_qapp(obj): ...

    def test_can_create(self, qtbot, monkeypatch, expenses_list, budgets_list, categories_sorted_list):
        monkeypatch.setattr(Qt6View, "_create_qapp", self.monkey_create_qapp)
        view = Qt6View()
        view.expenses.connect_get_attr_allowed(get_attr_allowed)
        view.expenses.set_contents(expenses_list)
        view.expenses.connect_get_default_entry(get_default_expense)
        view.budgets.connect_get_attr_allowed(get_attr_allowed)
        view.budgets.set_contents(budgets_list)
        view.categories.connect_get_attr_allowed(get_attr_allowed)
        view.categories.set_contents(categories_sorted_list)
        view.categories.connect_get_default_entry(get_default_category)
        qtbot.add_widget(view.window)
        view.window.show()