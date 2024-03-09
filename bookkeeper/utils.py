"""
Helper functions.
"""

from typing import Iterable, Iterator


def _get_indent(line: str) -> int:
    """
    Get the indentation of a line.

    Parameters
    ----------
    line : str
        line, maybe with left (heading) indentation.

    Returns
    -------
    Amount of indentation whitespace characters.
    """

    return len(line) - len(line.lstrip())


def _lines_with_indent(lines: Iterable[str]) -> Iterator[tuple[int, str]]:
    """
    Extract indention information from lines.

    Parameters
    ----------
    lines : Iterable[str]
        Iterable(i.e. file, list) of lines with heading indents.

    Returns
    -------
    Generator of pairs indent-line_with_indent.
    """

    for line in lines:
        if not line or line.isspace():
            continue
        yield _get_indent(line), line.strip()


def read_tree(lines: Iterable[str]) -> list[tuple[str, str | None]]:
    """
    Read tree structure from text, based on indentation.
    Converts text into a list of pairs(tuples) child-parent
    in topological order.
    Top-level parents are None.
    Empty lines are ignored.

    Example:
    Input:
    parent
        child1
            child2
        child3

    Output:
    [('parent', None), ('child1', 'parent'),
     ('child2', 'child1'), ('child3', 'parent')]

    Parameters
    ----------
    lines : Iterable[str]
        Iterable(i.e. file, list), containing lines in example-like format.

    Returns
    -------
    List of child-parent pairs(tuples).
    """

    parents: list[tuple[str | None, int]] = []
    last_indent = -1
    last_name = None
    result: list[tuple[str, str | None]] = []
    for i, (indent, name) in enumerate(_lines_with_indent(lines)):
        if indent > last_indent:
            parents.append((last_name, last_indent))
        elif indent < last_indent:
            while indent < last_indent:
                _, last_indent = parents.pop()
            if indent != last_indent:
                raise IndentationError(
                    f'unindent does not match any outer indentation '
                    f'level in line {i}:\n'
                )
        result.append((name, parents[-1][0]))
        last_name = name
        last_indent = indent
    return result
