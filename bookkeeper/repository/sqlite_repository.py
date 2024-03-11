"""
Sqlite3 repository.
"""

import sqlite3
from typing import Any
from datetime import datetime
from inspect import get_annotations

from bookkeeper.repository.abstract_repository import AbstractRepository, T


class SqliteRepository(AbstractRepository[T]):
    """
    Sqlite3 repository, stores data in a database.
    pk is the rowid, (0 is a valid ROWID,
    but it will never be automatically assigned by SQLite).

    Attributes
    ----------
    _db_filename : str
        Filename of the database file.
        TODO: config where name will be stored.
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
    _cls : type[T]
        class that is stored by current repository
    """

    _db_filename: str
    _table_name: str
    _fields: dict
    _names: str
    _placeholders: str
    _cls: type[T]

    def __init__(self, db_filename: str, cls: type[T]) -> None:
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
        self._names = ', '.join(self._fields.keys())
        self._placeholders = ', '.join("?" * len(self._fields))

    def _init_database(self):
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
        with sqlite3.connect(self._db_filename) as con:
            cur = con.cursor()
            # If the table has a column of type INTEGER PRIMARY KEY
            # then that column is another alias for the rowid. (sqlite doc)
            cur.execute(
                f'CREATE TABLE IF NOT EXISTS {self._table_name} (pk INTEGER PRIMARY KEY NOT NULL)'
            )
            # create fields
            for field in self._fields:
                # determine type of creatable field
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
                else:
                    raise TypeError(' '.join([
                         'Only int, float, str and datetime are supported.',
                        f'But {field} in {self._table_name} is {field_type}'
                    ]))
                # create the field
                try:
                    cur.execute(
                        f'ALTER TABLE {self._table_name} ADD COLUMN {field} {sql_type}'
                    )
                except sqlite3.DatabaseError:
                    # ignore exception here, it will be generated
                    # when trying to add existing column
                    pass
            cur.close()
        con.close()

    def _values_list_from_obj(self, obj):
        return [getattr(obj, x) for x in self._fields]

    def add(self, obj: T) -> int:
        if type(obj) != self._cls:
            raise ValueError('Trying to add an object to the repository of other type')
        if getattr(obj, 'pk', None) != 0:
            raise ValueError(f'Trying to add object {obj} with filled pk attr')
        with sqlite3.connect(self._db_filename) as con:
            cur = con.cursor()
            cur.execute('PRAGMA foreign_keys = ON')
            cur.execute(
                f'INSERT INTO {self._table_name} ({self._names}) VALUES ({self._placeholders})',
                self._values_list_from_obj(obj)
            )
            if cur.lastrowid is None:
                # unreachable, as if insert fails, execute will raise exception
                # needed to suppress mypy error marker
                raise sqlite3.DatabaseError('Lastrowid must be not None after insert')
            obj.pk = cur.lastrowid
            cur.close()
        con.close()
        return obj.pk

    def get(self, pk: int) -> T | None:
        obj = None
        with sqlite3.connect(self._db_filename) as con:
            cur = con.cursor()
            cur.execute(
                f'SELECT {self._names} from {self._table_name} where pk={pk}'
            )
            rows = cur.fetchall()
            # len(rows) is definitely 1, as pk is unique
            obj = self._cls()
            attr_values = iter(rows[0])
            for attr_str in self._fields.keys():
                # unlike int, float and str, datetime needs conversion
                if self._fields[attr_str] in (datetime, datetime | None):
                    setattr(obj, attr_str, datetime.strptime(next(attr_values), '%Y-%m-%d %H:%M:%S.%f'))
                else:
                    setattr(obj, attr_str, next(attr_values))
            cur.close()
        con.close()
        return obj

    def get_all(self, where: dict[str, Any] | None = None) -> list[T]:
        return []

    def update(self, obj: T) -> None:
        if type(obj) != self._cls:
            raise TypeError('Trying to update an object in the repository of other type')
        names_placeholders = ', '.join([f'{self._names[i]} = {self._placeholders[i]}'
                                        for i in range(len(self._names))])
        with sqlite3.connect(self._db_filename) as con:
            cur = con.cursor()
            cur.execute(
                f'UPDATE {self._table_name} SET {names_placeholders} WHERE pk = {obj.pk}',
                self._values_list_from_obj(obj)
            )
            if cur.rowcount == 0:
                # There was no object with this pk (i.e. pk == 0)
                raise ValueError('Trying to update absent object, have you added it?')
            cur.close()
        con.close()

    def delete(self, pk: int) -> None:
        pass
