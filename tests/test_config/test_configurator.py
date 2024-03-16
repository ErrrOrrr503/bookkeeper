import pytest

from bookkeeper.config.configurator import Configurator
from configparser import ConfigParser

@pytest.fixture
def def_configparser():
    cp = ConfigParser()
    cp['DEFAULT']['a'] = '1'
    cp['DEFAULT']['b'] = '~/db'
    return cp

@pytest.fixture
def def_config():
    return """
        [DEFAULT]
        a = 1
        b = ~/db
        """

def test_create_realconfig():
    # may fail if smth wrong in env
    conf = Configurator()
    c = ConfigParser()
    c.read('bookkeeper/config/config.ini')
    assert list(c) == list(conf._parser)

def test_get(tmp_path, def_configparser, def_config):
    confpath = tmp_path / 'config'
    with open(confpath, 'w') as cf:
        cf.write(def_config)
    conf = Configurator([(confpath, 'abs')])
    ref = def_configparser
    assert ref['DEFAULT'] == conf['DEFAULT']
    assert ref['DEFAULT']['a'] == conf['DEFAULT']['a']
    assert ref['DEFAULT']['b'] == conf['DEFAULT']['b']

def test_write(tmp_path, def_configparser, def_config):
    confpath = tmp_path / 'config'
    with open(confpath, 'w') as cf:
        cf.write(def_config)
    conf = Configurator([(confpath, 'abs')])
    conf['DEFAULT']['a'] = '2'
    conf.write()
    conf1 = Configurator([(confpath, 'abs')])
    ref = def_configparser
    ref['DEFAULT']['a'] = '2'
    assert ref['DEFAULT'] == conf1['DEFAULT']
    assert ref['DEFAULT']['a'] == conf1['DEFAULT']['a']
    assert ref['DEFAULT']['b'] == conf1['DEFAULT']['b']