"""
Expense category model
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterator, Any

from ..repository.abstract_repository import AbstractRepository


@dataclass
class Category:
    """
    Represents expense category.

    Attributes
    ----------
    name : str
        Name of the category.
    parent : int | None
        A link to the parent (it's id or pk).
        Parent is the the category of which this category is a subcategory.
        For top-level categories, parent = None.
    pk : int
        Primary key for storing the category in a repository.
    """

    name: str = 'Category'
    parent: int | None = None
    pk: int = 0

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name and self.parent == other.parent

    def get_parent(self,
                   repo: AbstractRepository['Category']) -> 'Category | None':
        """
        Get parent category as Category object.
        If called for top-level category, None is returned.

        Parameters
        ----------
        repo : AbstractRepository['Category']
            Repository from which object will be taken.

        Returns
        -------
        class Category instance or None
        """

        if self.parent is None:
            return None
        return repo.get(self.parent)

    def get_all_parents(self,
                        repo: AbstractRepository['Category']
                        ) -> Iterator['Category']:
        """
        Get all categories from this to top level one by one (generator).

        Parameters
        ----------
        repo : AbstractRepository['Category']
            Repository from which object will be taken.

        Yields
        -------
        class Category instances from patent and up till top level
        """

        parent = self.get_parent(repo)
        if parent is None:
            return
        yield parent
        yield from parent.get_all_parents(repo)

    @staticmethod
    def _get_children(graph: dict[int | None, list['Category']],
                     root: int | None) -> Iterator['Category']:
        """ dfs in graph from root """
        for subcat in graph[root]:
            yield subcat
            yield from Category._get_children(graph, subcat.pk)

    def get_subcategories(self,
                          repo: AbstractRepository['Category']
                          ) -> Iterator['Category']:
        """
        Get all subcategories: all subcategories of this,
        their subcategories, etc.

        Parameters
        ----------
        repo : AbstractRepository['Category']
            Repository from which object will be taken.

        Yields
        -------
        class Category instances, which are subcategories
        of different level lower than this.
        """

        subcats = defaultdict(list)
        for cat in repo.get_all():
            subcats[cat.parent].append(cat)
        return self._get_children(subcats, self.pk)

    @classmethod
    def get_all_categories_sorted(
            cls,
            repo: AbstractRepository['Category']) -> Iterator['Category']:
        subcats = defaultdict(list)
        for cat in repo.get_all():
            subcats[cat.parent].append(cat)
        return cls._get_children(subcats, None)

    @classmethod
    def create_from_tree(
            cls,
            tree: list[tuple[str, str | None]],
            repo: AbstractRepository['Category']) -> list['Category']:
        """
        Create category tree from a list of "child-parent" pairs (tree).
        The list must be sorted in the way children don't appear
        before their parent, there is no correctness checks.
        When using DBMS with external keys checks - error will be raised
        (for sqlite3 - IntegrityError).
        When no checks are performed by DBMS - result might be correct
        (if only input data is correct, except for sorting).

        Parameters
        ----------
        tree : list[tuple[str, str | None]]
            List of "child-parent" pairs.
        repo : AbstractRepository['Category']
            Repository in which objects will be saved.

        Returns
        -------
        List of created Category instances.
        """

        created: dict[str, Category] = {}
        for child, parent in tree:
            cat = cls(child,
                      created[parent].pk if parent is not None else None)
            repo.add(cat)
            created[child] = cat
        return list(created.values())
