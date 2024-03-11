from bookkeeper.repository.sqlite_repository import SqliteRepository
from datetime import datetime

import pytest

@pytest.fixture
def empty_class():
    class Empty():
        pk: int = 0

    return Empty

@pytest.fixture
def good_class():
    class Good():
        pk: int = 0
        integer: int = 146
        floating: float = 146.0
        literal: str = 'hello world'
        datetype: datetime = datetime.now()

        def __eq__(self, other):
            if not isinstance(other, Good):
                return NotImplemented
            return self.integer == other.integer \
               and self.floating == other.floating \
               and self.literal == other.literal \
               and self.datetype == other.datetype



    return Good

@pytest.fixture
def bad_attribute_class():
    class Bad():
        pk: int = 0
        integer: int = 146
        lst: list = [1, 2]

    return Bad

@pytest.fixture
def bad_annotation_class():
    class Bad():
        pk = 0

    return Bad

@pytest.fixture
def bad_no_pk_class():
    class Bad():
        id: int = 0
        integer: int = 146
        floating: float = 146.0
        literal: str = 'hello world'
        datetype: datetime = datetime.now()

    return Bad

@pytest.fixture
def good_other_class():
    class GoodOther():
        pk: int = 0
        integer: int = 146
        floating: float = 146.0
        literal: str = 'hello world'
        datetype: datetime = datetime.now()

    return GoodOther

@pytest.mark.parametrize('custom_class', ['good_class'])
def test_init(tmp_path, custom_class, request):
    cls = request.getfixturevalue(custom_class)
    db_filename = tmp_path / 'temp.db'
    SqliteRepository(db_filename = db_filename, cls = cls)

def test_cant_store_empty(tmp_path, empty_class):
    cls = empty_class
    db_filename = tmp_path / 'temp.db'
    with pytest.raises(TypeError):
        SqliteRepository(db_filename = db_filename, cls = cls)

@pytest.mark.parametrize('custom_class', ['good_class'])
def test_crud_new_db(tmp_path, custom_class, request):
    cls = request.getfixturevalue(custom_class)
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    obj = cls()
    pk = repo.add(obj)
    assert obj.pk == pk
    obj1 = repo.get(pk)
    assert repo.get(pk) == obj
    #obj2 = custom_class()
    #obj2.pk = pk
    #repo.update(obj2)
    #assert repo.get(pk) == obj2
    #repo.delete(pk)
    #assert repo.get(pk) is None

@pytest.mark.parametrize('custom_class', ['good_class'])
def test_crud_existing_db(tmp_path, custom_class, request):
    cls = request.getfixturevalue(custom_class)
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    # create and fill db
    obj = cls()
    pk = repo.add(obj)
    assert obj.pk == pk
    assert repo.get(pk) == obj

    repo1 = SqliteRepository(db_filename = db_filename, cls = cls)
    obj1 = cls()
    pk1 = repo1.add(obj1)
    assert obj1.pk == pk1
    assert repo1.get(pk1) == obj1

@pytest.mark.parametrize('custom_class', ['good_class'])
def test_cannot_add_with_filled_pk(tmp_path, custom_class, request):
    cls = request.getfixturevalue(custom_class)
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    obj = cls()
    obj.pk = 1
    with pytest.raises(ValueError):
        repo.add(obj)

def test_unsupported_attribute_types(tmp_path, bad_attribute_class):
    cls = bad_attribute_class
    db_filename = tmp_path / 'temp.db'
    with pytest.raises(TypeError):
        SqliteRepository(db_filename = db_filename, cls = cls)

@pytest.mark.parametrize('custom_class', ['bad_annotation_class', 'bad_no_pk_class'])
def test_cannot_init_without_pk(tmp_path, custom_class, request):
    cls = request.getfixturevalue(custom_class)
    db_filename = tmp_path / 'temp.db'
    with pytest.raises(TypeError):
        SqliteRepository(db_filename = db_filename, cls = cls)


def test_cannot_add_other_type(tmp_path, good_class, good_other_class):
    cls = good_class
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    obj = good_other_class
    with pytest.raises(ValueError):
        repo.add(obj)