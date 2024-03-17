"""
Factory to abstract from preferred repository
"""

from typing import Generic

from bookkeeper.repository.abstract_repository import AbstractRepository, T
from bookkeeper.repository.memory_repository import MemoryRepository
from bookkeeper.repository.sqlite_repository import SqliteRepository
from bookkeeper.config.configurator import Configurator


class RepositoryFactory(Generic[T]):
    """
    Creates repositories according to config and stored type.

    Relevant configuration:
    [RepositoryFactory]
    desired_repo = [MemoryRepository | SqliteRepository]

    Attributes
    ----------
    _desired_repo : type[AbstractRepository[T]]
        Repo type to create.
    """

    _desired_repo: type[AbstractRepository[T]]

    def __init__(self, desired_repo: type[AbstractRepository[T]] | None = None):
        if desired_repo is not None:
            self._desired_repo = desired_repo
        else:
            self._init_configuration()

    def _init_configuration(self) -> None:
        confer = Configurator()
        desired_str = confer[type(self).__name__]['desired_repo']
        if desired_str == 'MemoryRepository':
            self._desired_repo = MemoryRepository[T]
        elif desired_str == 'SqliteRepository':
            self._desired_repo = SqliteRepository[T]
        else:
            raise ValueError(
                f'Unknown repo \'{desired_str}\'specified in configuration.'
            )

    def repo_for(self, stored_type: type[T]) -> AbstractRepository[T]:
        """
        Construct repo for given stored type
        """
        return self._desired_repo(cls=stored_type)
