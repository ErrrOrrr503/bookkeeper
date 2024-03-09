"""
Simple sample script for command line.
"""

from bookkeeper.models.category import Category
from bookkeeper.models.expense import Expense
from bookkeeper.repository.memory_repository import MemoryRepository
from bookkeeper.utils import read_tree

cat_repo = MemoryRepository[Category]()
exp_repo = MemoryRepository[Expense]()

cats = '''
foodstuff
    meat
        raw meat
        meat products
    candies
books
clothing
'''.splitlines()

Category.create_from_tree(read_tree(cats), cat_repo)

while True:
    try:
        cmd = input('$> ')
    except EOFError:
        break
    if not cmd:
        continue
    if cmd == 'categories':
        print(*cat_repo.get_all(), sep='\n')
    elif cmd == 'expenses':
        print(*exp_repo.get_all(), sep='\n')
    elif cmd[0].isdecimal():
        amount, name = cmd.split(maxsplit=1)
        try:
            cat = cat_repo.get_all({'name': name})[0]
        except IndexError:
            print(f'category {name} not found')
            continue
        exp = Expense(int(amount), cat.pk)
        exp_repo.add(exp)
        print(exp)
