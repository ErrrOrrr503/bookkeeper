from bookkeeper.repository.repository_factory import RepositoryFactory
from bookkeeper.repository.memory_repository import MemoryRepository
from bookkeeper.repository.sqlite_repository import SqliteRepository
from bookkeeper.config.configurator import Configurator
from bookkeeper.models.category import Category
from bookkeeper.models.budget import Budget
from bookkeeper.models.expense import Expense

from datetime import datetime

import pytest

@pytest.fixture
def category():
    return Category('cat')

@pytest.fixture
def budget():
    return Budget(146)

@pytest.fixture
def expense():
    return Expense(146, 1)

@pytest.fixture(scope='session')
def sqlite_configurator(tmp_path_factory):
    conffile = tmp_path_factory.mktemp('tmp') / 'config.ini'
    dbfile = tmp_path_factory.mktemp('tmp') / 'temp.db'
    with open(conffile, 'w') as cf:
        cf.write(f"""
            [SqliteRepository]
            db_file = {dbfile}

            [RepositoryFactory]
            desired_repo = SqliteRepository
        """)
    return Configurator([(conffile, 'abs')])

@pytest.fixture(scope='session')
def memory_configurator(tmp_path_factory):
    conffile = tmp_path_factory.mktemp('tmp') / 'config.ini'
    with open(conffile, 'w') as cf:
        cf.write(f"""
            [RepositoryFactory]
            desired_repo = MemoryRepository
        """)
    return Configurator([(conffile, 'abs')])

@pytest.fixture(scope='session')
def badrepo_configurator(tmp_path_factory):
    conffile = tmp_path_factory.mktemp('tmp') / 'config.ini'
    with open(conffile, 'w') as cf:
        cf.write(f"""
            [RepositoryFactory]
            desired_repo = Repository404
        """)
    return Configurator([(conffile, 'abs')])

@pytest.mark.parametrize('custom_configurator', ['sqlite_configurator', 'memory_configurator'])
def test_can_read_config(custom_configurator, request):
    custom_configurator = request.getfixturevalue(custom_configurator)
    def_config_files = Configurator.config_files
    Configurator.config_files = custom_configurator.config_files
    rf = RepositoryFactory()
    assert rf._desired_repo.__name__ == Configurator()['RepositoryFactory']['desired_repo']
    Configurator.config_files = def_config_files

def test_bad_config(badrepo_configurator):
    def_config_files = Configurator.config_files
    Configurator.config_files = badrepo_configurator.config_files
    with pytest.raises(ValueError):
        RepositoryFactory()
    Configurator.config_files = def_config_files

@pytest.mark.parametrize('custom_configurator', ['sqlite_configurator', 'memory_configurator'])
@pytest.mark.parametrize('obj', ['category', 'expense', 'budget'])
def test_can_create_repo(custom_configurator, obj, request):
    custom_configurator = request.getfixturevalue(custom_configurator)
    obj = request.getfixturevalue(obj)
    def_config_files = Configurator.config_files
    Configurator.config_files = custom_configurator.config_files
    rf = RepositoryFactory()
    repo = rf.repo_for(type(obj))
    pk = repo.add(obj)
    assert repo.get(pk) == obj
    assert repo.get_all() == [obj]
    assert repo.get_all({'pk': pk}) == [obj]
    assert repo.get_all({'pk': 0}) == []
    repo.delete(pk)
    assert repo.get(pk) == None
    assert repo.get_all() == []
    with pytest.raises(KeyError):
        repo.delete(pk)
    Configurator.config_files = def_config_files

def test_can_create_from_param():
    RepositoryFactory(MemoryRepository)