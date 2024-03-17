"""
The module contains a description of the abstract repository
(in fact, interface).

The repository implements object storage by assigning each object a unique
identifier (id) in the primary key (pk) attribute.
Objects that can be saved in the repository must support adding the pk
attribute and must not use it for other purposes.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Protocol, Any


class Model(Protocol):  # pylint: disable=too-few-public-methods
    """
    Model must contain pk attribute.
    Model must contain only int, float, str, datetime or timedelta.
    Model can contain attributes of any arbitrary names, except pk.
        => Implementations must not depend on anything except the pk,
        i.e. rowid in sqlite3.
    Model must contain at least one attribute besides pk
        (also, some repos may handle empty objects)

    Attributes
    ----------
    pk : int
        Number to be used as primary key and id.
        Initial aka empty value is 0.
    """

    pk: int


T = TypeVar('T', bound=Model)
""" T is a type template of a type that follows Model protocol. """


class AbstractRepository(ABC, Generic[T]):
    """
    Repository for type[T] objects abstract class.
    """

    @abstractmethod
    def __init__(self, cls: type[T] | None = None):
        """
        Init the repo according to the given type.
        Implementations may, or may not use cls, but have to accept it.
        (as it is crucial for i.e. sqlite implementation)
        """
        raise NotImplementedError("Must implement this!")

    @abstractmethod
    def add(self, obj: T) -> int:
        """
        Add an object to the repository.
        Generates object 'id' which is written into object and returned.

        Parameters
        ----------
        obj : T
            Object to be added. 'id' is written into object.pk attribute.

        Returns
        -------
        Generated object's 'id'.
        """

        raise NotImplementedError("Must implement this!")

    @abstractmethod
    def get(self, pk: int) -> T | None:
        """
        Get an object from the repository.

        Parameters
        ----------
        pk : int
            id, by which to retrieve an object

        Returns
        -------
        Object of type T or None if no object is found.
        """

        raise NotImplementedError("Must implement this!")

    @abstractmethod
    def get_all(self, where: dict[str, Any] | None = None) -> list[T]:
        """
        Get all objects by some condition.

        Parameters
        ----------
        where : dict[str, Any] | None
            Condition in the form of a dict['name_of_the_field': field_value]
            or None.
            If where is None (default), return all objects, stored in repo.

        Returns
        -------
        List of objects that match the condition, may be empty.
        """

        raise NotImplementedError("Must implement this!")

    @abstractmethod
    def update(self, obj: T) -> None:
        """
        Update the object's properties in the repository.

        Parameters
        ----------
        obj : T
            Object with new properties, but not modified pk.

        Returns
        -------
        None
        """

        raise NotImplementedError("Must implement this!")

    @abstractmethod
    def delete(self, pk: int) -> None:
        """
        Delete the object, referred to by pk from the repository.

        Parameters
        ----------
        pk : int
            The primary key of the object to be deleted.

        Returns
        -------
        None
        """

        raise NotImplementedError("Must implement this!")
