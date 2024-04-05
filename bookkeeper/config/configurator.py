"""
Configurator module
"""
from configparser import ConfigParser
from typing import Any
import os
# only for determining project path
import bookkeeper


class Configurator():
    """
    Configurator - config manager for bookkeeper.
    Needed to provide abstraction over configs.
    I.e if we will need to make bookkeeper a package on a multi-user system.

    Attributes
    ----------
    config_files : list[tuple[str, str]]
        List of config filenames(first str) and filename types(second str).
        All configs are read. Last one is written.
        This is done for loading default conf, but writing i.e. user one.
        All paths are expanduser-d.
    parser : ConfigParser
        ConfigParser that will held all config operations.
    _writefilename : str
        Prepared filename of the last config_file.
        To write config into.
    """

    config_files: list[tuple[str, str]] = [
        ('config/config.ini', 'prj_rel'),
        ('config.ini', 'rel')  # will be written
    ]
    _parser: ConfigParser = ConfigParser()
    _writefilename: str

    def __init__(self, config_files: list[tuple[str, str]] | None = None):
        if config_files is not None:
            self.config_files = config_files
        prj_dir = os.path.dirname(bookkeeper.__file__)
        confpath = ''
        for conf in self.config_files:
            confpath = os.path.expanduser(conf[0])
            if conf[1] == 'prj_rel':
                confpath = prj_dir + '/' + confpath
            self._parser.read(confpath)
        self._writefilename = confpath

    def __getitem__(self, item_name: str) -> Any:
        return self._parser[item_name]

    def write(self) -> None:
        """ Write the _writefilename config file. """
        with open(self._writefilename, 'w') as writefile:
            self._parser.write(writefile)
