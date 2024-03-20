from bookkeeper.repository.abstract_repository import AbstractRepository

import pytest


def test_cannot_create_abstract_repository():
    with pytest.raises(TypeError):
        AbstractRepository()


def test_can_create_subclass():
    class Test(AbstractRepository):
        def __init__(self, cls = None): pass
        def add(self, obj): return 0
        def get(self, pk): pass
        def get_all(self, where=None): return []
        def update(self, obj): pass
        def delete(self, pk): pass

    t = Test()
    assert isinstance(t, AbstractRepository)

def test_cant_create_subclass_without_overriding():
    class Test(AbstractRepository):
        def __init__(self, cls = None): pass
        def get(self, pk): pass
        def get_all(self, where=None): return []
        def update(self, obj): pass
        def delete(self, pk): pass

    with pytest.raises(TypeError):
        t = Test()
