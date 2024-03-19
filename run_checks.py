"""
Small script for automating running tests, linters, mb other checkers.
"""

import subprocess
import sys
import re
from typing import Callable

from _pytest.nodes import _check_initialpaths_for_relpath

class Checker():
    """
    Runs checker command and validates the result.
    """
    cmd: str
    name: str
    print_output: bool = True
    expected_retcode: int | None = 0
    output_hook: Callable[[str], int] | None = None

    def __init__(self, name: str, cmd: str, expected_retcode: int | None = 0, print_output: bool = True, output_hook: Callable[[str], int] | None = None):
        self.expected_retcode = expected_retcode
        self.cmd = cmd
        self.name = name
        self.print_output = print_output
        self.output_hook = output_hook

    def run(self) -> int:
        print(f"######## Running {self.name} ... ", end="\n" if self.print_output else "")
        ret: int = 0
        try:
            res = subprocess.check_output(args = self.cmd, shell = True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            res = e.output
            ret = e.returncode
        finally:
            if self.print_output:
                sys.stdout.buffer.write(res)
                #print(res.decode("utf-8"))
            if self.output_hook and ret == 0:
                ret = self.output_hook(res.decode("utf-8"))
        if self.expected_retcode is None or ret == self.expected_retcode:
            print(f"######## {self.name} OK!" if self.print_output else "OK!")
        else:
            print(f"######## {self.name} FAIL!" if self.print_output else "FAIL!")
        return ret

def pylint_check_score(output: str) -> int:
    found = re.search("^Your code has been rated at ([0-9]\.[0-9]+)/10", output)
    if found:
        score = float(found.group(1))
        if score >= 9:
            return 0
    return -1

###############################################################################

checks: list[Checker] = []
verbose = True

checks.append(Checker("tests", "pytest --cov", print_output=verbose))
checks.append(Checker("mypy", "mypy --strict bookkeeper", print_output=verbose))
checks.append(Checker("pylint", "pylint --extension-pkg-whitelist=PySide6 bookkeeper", expected_retcode=None, print_output=verbose, output_hook=pylint_check_score))
checks.append(Checker("flake8", "flake8 bookkeeper", print_output=verbose))

###############################################################################

for checker in checks:
    checker.run()
