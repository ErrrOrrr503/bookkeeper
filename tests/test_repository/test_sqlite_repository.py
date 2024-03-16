from bookkeeper.repository.sqlite_repository import SqliteRepository
from bookkeeper.config.configurator import Configurator
from datetime import datetime, timedelta

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
        timedel: timedelta = datetime.now() - datetime(1970, 1, 1)

        def __eq__(self, other):
            if not isinstance(other, Good):
                return NotImplemented
            return self.integer == other.integer \
               and self.floating == other.floating \
               and self.literal == other.literal \
               and self.datetype == other.datetype \
               and self.timedel == other.timedel

        def __lt__(self, other):
            if not isinstance(other, Good):
                return NotImplemented
            return self.pk < other.pk


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
        timedel: timedelta = datetime.now() - datetime(1970, 1, 1)

    return Bad

@pytest.fixture
def good_other_class():
    class GoodOther():
        pk: int = 0
        integer: int = 146
        floating: float = 146.0
        literal: str = 'hello world'
        datetype: datetime = datetime.now()
        timedel: timedelta = datetime.now() - datetime(1970, 1, 1)

    return GoodOther

@pytest.fixture(scope='session')
def custom_configurator(tmp_path_factory):
    conffile = tmp_path_factory.mktemp('tmp') / 'config.ini'
    dbfile = tmp_path_factory.mktemp('tmp') / 'temp.db'
    with open(conffile, 'w') as cf:
        cf.write(f"""
            [SqliteRepository]
            db_file = {dbfile}
        """)
    return Configurator([(conffile, 'abs')])

def test_init(tmp_path, good_class):
    cls = good_class
    db_filename = tmp_path / 'temp.db'
    SqliteRepository(db_filename = db_filename, cls = cls)

def test_cant_store_empty(tmp_path, empty_class):
    cls = empty_class
    db_filename = tmp_path / 'temp.db'
    with pytest.raises(TypeError):
        SqliteRepository(db_filename = db_filename, cls = cls)

def test_crud_new_db(tmp_path, good_class):
    cls = good_class
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    obj = cls()
    pk = repo.add(obj)
    assert obj.pk == pk
    assert repo.get(pk) == obj
    obj1 = cls()
    obj1.pk = pk
    obj1.integer = 641
    repo.update(obj1)
    assert repo.get(pk) == obj1
    repo.delete(pk)
    assert repo.get(pk) is None

def test_crud_existing_db(tmp_path, good_class):
    cls = good_class
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    # create and fill db
    obj = cls()
    pk = repo.add(obj)
    assert obj.pk == pk
    assert repo.get(pk) == obj

    # repo1 uses db, created by repo
    repo1 = SqliteRepository(db_filename = db_filename, cls = cls)
    obj1 = cls()
    pk1 = repo1.add(obj1)
    assert obj1.pk == pk1
    assert repo1.get(pk1) == obj1
    obj2 = cls()
    obj2.pk = pk
    obj2.integer = 641
    repo.update(obj2)
    assert repo.get(pk) == obj2
    repo.delete(pk)
    assert repo.get(pk) is None

def test_cannot_add_with_filled_pk(tmp_path, good_class):
    cls = good_class
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

def test_cannot_update_other_type(tmp_path, good_class, good_other_class):
    cls = good_class
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    obj = good_class()
    pk = repo.add(obj)
    obj1 = good_other_class
    obj1.pk = pk
    with pytest.raises(ValueError):
        repo.update(obj1)

def test_cannot_update_absent(tmp_path, good_class):
    cls = good_class
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    obj = good_class()
    # pk = 0
    with pytest.raises(ValueError):
        repo.update(obj)
    obj.pk = 146
    with pytest.raises(ValueError):
        repo.update(obj)

def test_cannot_delete_absent(tmp_path, good_class):
    cls = good_class
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    with pytest.raises(KeyError):
        repo.delete(0)
    with pytest.raises(KeyError):
        repo.delete(146)

def test_get_all(tmp_path, good_class):
    cls = good_class
    db_filename = tmp_path / 'temp.db'
    repo = SqliteRepository(db_filename = db_filename, cls = cls)

    assert repo.get_all() == []

    obj_list = []
    dt = datetime.now()
    for _ in range(5):
        obj = cls()
        obj.datetype = dt
        repo.add(obj)
        obj_list.append(obj)
    assert repo.get_all().sort() == obj_list.sort()

    assert repo.get_all({'pk': obj_list[0].pk}) == [ obj_list[0] ]
    assert obj_list.sort() == repo.get_all({'integer': obj_list[0].integer,
                                            'floating': obj_list[0].floating,
                                            'literal': obj_list[0].literal,
                                            'datetype': obj_list[0].datetype,
                                            'timedel': obj_list[0].timedel}).sort()

def test_configurator_can_create_default(good_class, custom_configurator):
    cls = good_class
    def_config_files = Configurator.config_files
    Configurator.config_files = custom_configurator.config_files
    repo = SqliteRepository(cls)
    conf = Configurator()
    assert repo._db_filename == conf['SqliteRepository']['db_file']
    Configurator.config_files = def_config_files

def test_configurator_crud(good_class, custom_configurator):
    cls= good_class
    repo = SqliteRepository(cls = cls, custom_configurator=custom_configurator)

    obj = cls()
    pk = repo.add(obj)
    assert obj.pk == pk
    assert repo.get(pk) == obj
    obj1 = cls()
    obj1.pk = pk
    obj1.integer = 641
    repo.update(obj1)
    assert repo.get(pk) == obj1
    repo.delete(pk)
    assert repo.get(pk) is None