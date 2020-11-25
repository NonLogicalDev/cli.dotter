from __future__ import annotations
from typing import List

from pathlib import PosixPath


def path_matches_patterns(path: PosixPath, patterns: List[str]) -> bool:
    for ignore_pattern in patterns:
        if path.match(ignore_pattern):
            return True
    return False


def coalesce(*args):
    for arg in args:
        if arg is not None:
            return arg
