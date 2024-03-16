"""
Sqlite3 repository.
"""

import sqlite3
from typing import Any
from datetime import datetime, timedelta
from inspect import get_annotations
from contextlib import closing
from os.path import expanduser

from bookkeeper.repository.abstract_repository import AbstractRepository, T
from bookkeeper.config.configurator import Configurator


class SqliteRepository(AbstractRepository[T]):
    """
    Sqlite3 repository, stores data (models) in a database.

    The repo creates db file if not already exists.
    Creates table, named according to __name__ attribute of the stored class.
    The table contains fields, names according to attributes of the stored class.
    As __name__ and attribute names can't contain sql injections, they are used directly.
    Contents of the fields are protected with placeholders
    (in fact sqlite3 lib supports placeholders only for values).

    pk is the rowid, (0 is a valid ROWID,
    but it will never be automatically assigned by SQLite).

    The repository can explicitly hold non standart for db types,
    i.e. datetime and timedelta. Handling is perfomed in _sql_type
    methods.

    Attributes
    ----------
    _db_filename : str
        Filename of the database file.
    _table_name : str
        Name of the database table. Matches the name of the class that stored.
    _fields : dict
        Names of the table fields.
        Generated from annotations in the class stored.
    _names : str
        Helper string, containing stored attributes' names.
        For usage in sql queries.
    _placeholders : str
        Helper string, containing question marks -
        placeholders for values, that correspond to _names.
        For usage in sql queries.
    _names_placeholders : str
        Helper string, containing <name> = ?, ... construction
        with attribute names and placeholders for corresponding values.
        For usage in sql queries (update).
    _cls : type[T]
        class that is stored by current repository
    """

    _db_filename: str
    _table_name: str
    _fields: dict[str, type]
    _names: str
    _placeholders: str
    _names_placeholders: str
    _cls: type[T]

    def __init__(self, cls: type[T], db_filename: str | None = None,
                 custom_configurator: Configurator | None = None) -> None:
        self._init_configuration(custom_configurator)
        if db_filename is not None:
            self._db_filename = db_filename
        self._cls = cls
        self._table_name = cls.__name__.lower()
        self._fields = get_annotations(cls, eval_str=True)
        if self._fields.get('pk') != int:
            raise TypeError(f'{cls} must have pk: int attribute and annotations')
        self._fields.pop('pk', None)
        if len(self._fields) == 0:
            # we need at least some data to SELECT and INSERT
            raise TypeError(
                f'{cls} must have at least one attribute besides pk - be not empty.'
            )
        self._init_database()
        self._init_helper_strings()

    def _init_configuration(self, confer: Configurator | None) -> None:
        """
        Init attributes according to configurator.
        Generally, default Configurator() is used.
        Custom confer is only for testing purposes.
        """
        if confer is None:
            confer = Configurator()
        self._db_filename = expanduser(confer[type(self).__name__]['db_file'])

    def _init_helper_strings(self) -> None:
        attr_names = list(self._fields.keys())
        attr_placeholders = "?" * len(self._fields)
        self._names = ', '.join(attr_names)
        self._placeholders = ', '.join(attr_placeholders)
        self._names_placeholders = ', '.join([f'{attr_names[i]} = {attr_placeholders[i]}'
                                             for i in range(len(attr_names))])

    def _init_database(self) -> None:
        """
        Creates table according to fields and table name.

        By far no integrity checks are performed.
        If the database is capable of creating a table with desired name
        or an existing table is capable of adding columns and has 'pk',
        everything will seem ok.
        One can substitute/alter db file and mess with pk field.
        TODO: verify that pk is primary key + integrity.

        Non-init methods will rely on init integrity check and can assume db is correct.
        """
        with (closing(sqlite3.connect(self._db_filename)) as con,
              con as con,
              closing(con.cursor()) as cur):
            # If the table has a column of type INTEGER PRIMARY KEY
            # then that column is another alias for the rowid. (sqlite doc)
            cur.execute(
                f'CREATE TABLE IF NOT EXISTS {self._table_name}'
                '(pk INTEGER PRIMARY KEY NOT NULL)'
            )
            # create fields
            for field in self._fields:
                sql_type = self._sql_type_for_field(field)
                # create the field
                try:
                    cur.execute(
                        f'ALTER TABLE {self._table_name} ADD COLUMN {field} {sql_type}'
                    )
                except sqlite3.DatabaseError:
                    # ignore exception here, it will be generated
                    # when trying to add existing column
                    pass

    def _sql_type_for_field(self, field: str) -> str:
        """
        Return sql type according to field type.
        I.e. 'TEXT' for 'line' of type str.
        """
        field_type = self._fields[field]
        sql_type = None
        if field_type in (int, int | None):
            sql_type = 'INTEGER'
        elif field_type in (float, float | None):
            sql_type = 'REAL'
        elif field_type in (str, str | None):
            sql_type = 'TEXT'
        elif field_type in (datetime, datetime | None):
            sql_type = 'TEXT'
        elif field_type in (timedelta, timedelta | None):
            sql_type = 'TEXT'
        else:
            raise TypeError(
                'Only int, float, str, datetime and timedelta are supported.'
                f'But {field} in {self._table_name} is {field_type}'
            )
        return sql_type

    def _type_to_sql_type(self, value: Any) -> Any:
        """ Convert (prepare) type for saving to db """
        if type(value) == timedelta:
            # store timedelta as str
            # 'days seconds microseconds'
            # to allow absolute ranges and percision
            days = str(value.days)
            secs = str(value.seconds)
            usecs = str(value.microseconds)
            return ' '.join([days, secs, usecs])
        return value

    def _sql_typed_setattr(self, obj: T, attr_str: str, value: Any) -> None:
        """ Type-aware setattr """
        if (self._fields[attr_str] in (datetime, datetime | None)
                and isinstance(value, str)):
            setattr(obj, attr_str,
                    datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f'))
        elif (self._fields[attr_str] in (timedelta, timedelta | None)
              and isinstance(value, str)):
            d_s_us = value.split()
            tmdel = timedelta(days=int(d_s_us[0]),
                              seconds=int(d_s_us[1]),
                              microseconds=int(d_s_us[2]))
            setattr(obj, attr_str, tmdel)
        else:
            setattr(obj, attr_str, value)

    def _values_list_from_obj(self, obj: T) -> list[Any]:
        return [self._type_to_sql_type(getattr(obj, x)) for x in self._fields]

    def add(self, obj: T) -> int:
        if type(obj) != self._cls:
            raise ValueError('Trying to add an object to the repository of other type')
        if getattr(obj, 'pk', None) != 0:
            raise ValueError(f'Trying to add object {obj} with filled pk attr')
        with (closing(sqlite3.connect(self._db_filename)) as con,
              con as con,
              closing(con.cursor()) as cur):
            cur.execute('PRAGMA foreign_keys = ON')
            cur.execute(
                (f'INSERT INTO {self._table_name} ({self._names})'
                 f'VALUES ({self._placeholders})'),
                self._values_list_from_obj(obj)
            )
            if cur.lastrowid is None:
                # unreachable, as if insert fails, execute will raise exception
                # needed to suppress mypy error marker
                raise sqlite3.DatabaseError('Lastrowid must be not None after insert')
            obj.pk = cur.lastrowid
        return obj.pk

    def get(self, pk: int) -> T | None:
        obj = None
        with (closing(sqlite3.connect(self._db_filename)) as con,
              con as con,
              closing(con.cursor()) as cur):
            cur.execute(
                f'SELECT {self._names} FROM {self._table_name} WHERE pk={pk}'
            )
            rows = cur.fetchall()
            # len(rows) is 0 or 1, as pk is unique
            if len(rows) == 1:
                obj = self._cls()
                attr_values = iter(rows[0])
                for attr_str in self._fields.keys():
                    self._sql_typed_setattr(obj, attr_str, next(attr_values))
        return obj

    def get_all(self, where: dict[str, Any] | None = None) -> list[T]:
        ret_list = []
        with (closing(sqlite3.connect(self._db_filename)) as con,
              con as con,
              closing(con.cursor()) as cur):
            if where is not None:
                cur.execute(
                    f'SELECT {self._names} FROM {self._table_name}' +
                    ' WHERE ' + ' AND '.join([f'{name} = ?' for name in where.keys()]),
                    [self._type_to_sql_type(where[name]) for name in where.keys()]
                )
            else:
                cur.execute(
                    f'SELECT {self._names} FROM {self._table_name}'
                )
            rows = cur.fetchall()
            # len(rows) is 0 or 1, as pk is unique
            for row in rows:
                obj = self._cls()
                attr_values = iter(row)
                for attr_str in self._fields.keys():
                    self._sql_typed_setattr(obj, attr_str, next(attr_values))
                ret_list.append(obj)
        return ret_list

    def update(self, obj: T) -> None:
        if type(obj) != self._cls:
            raise ValueError('Trying to update an object'
                             'in the repository of other type')
        with (closing(sqlite3.connect(self._db_filename)) as con,
              con as con,
              closing(con.cursor()) as cur):
            cur.execute(
                (f'UPDATE {self._table_name} SET {self._names_placeholders}'
                 f'WHERE pk = {obj.pk}'),
                self._values_list_from_obj(obj)
            )
            if cur.rowcount == 0:
                # There was no object with this pk (i.e. pk == 0)
                raise ValueError('Trying to update absent object, have you added it?')

    def delete(self, pk: int) -> None:
        with (closing(sqlite3.connect(self._db_filename)) as con,
              con as con,
              closing(con.cursor()) as cur):
            cur.execute(
                f'DELETE FROM {self._table_name} WHERE pk = {pk}'
            )
            if cur.rowcount == 0:
                # There was no object with this pk (i.e. pk == 0)
                raise KeyError('Trying to delete absent object.')
