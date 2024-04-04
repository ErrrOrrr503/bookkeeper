from bookkeeper.view.abstract_view import AbstractEntries, T
from typing import Callable

import pytest

def test_entries_cannot_create_abstract():
    with pytest.raises(TypeError):
        AbstractEntries()


def test_entries_can_create_subclass():
    class Test(AbstractEntries[T]):
        def set_contents(self, entries: list[T]) -> None: pass
        def set_at_position(self, position: int, entry: T) -> None: pass
        def connect_edited(self, callback: Callable[[int, T], None]) -> None: pass
        def connect_delete(self, callback: Callable[[list[int]], None]) -> None: pass
        def connect_add(self, callback: Callable[[T], None]) -> None: pass
        def connect_get_attr_allowed(self, callback: Callable[[str], list[str]]) -> None: pass
        def connect_get_default_entry(self, callback: Callable[[], T]) -> None: pass

    t = Test()
    assert isinstance(t, AbstractEntries)

def test_entries_cant_create_subclass_without_overriding():
    class Test(AbstractEntries[T]):
        def set_at_position(self, position: int, entry: T) -> None: pass
        def connect_edited(self, callback: Callable[[int, T], None]) -> None: pass
        def connect_get_attr_allowed(self, callback: Callable[[str], list[str]]) -> None: pass

    with pytest.raises(TypeError):
        t = Test()

def test_entries_optional_methods():
    class Test(AbstractEntries[T]):
        def set_contents(self, entries: list[T]) -> None: pass
        def set_at_position(self, position: int, entry: T) -> None: pass
        def connect_edited(self, callback: Callable[[int, T], None]) -> None: pass
        def connect_delete(self, callback: Callable[[list[int]], None]) -> None: pass
        def connect_add(self, callback: Callable[[T], None]) -> None: pass
        def connect_get_attr_allowed(self, callback: Callable[[str], list[str]]) -> None: pass
        def connect_get_default_entry(self, callback: Callable[[], T]) -> None: pass

    t = Test()
    assert isinstance(t, AbstractEntries)
    with pytest.raises(NotImplementedError):
        t.color_entry(0, 0, 0, 0)