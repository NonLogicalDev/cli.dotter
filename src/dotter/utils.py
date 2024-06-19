from pathlib import PosixPath
from typing import Iterable, TypeVar


T = TypeVar('T')


def coalesce(*args: T) -> T:
    for arg in args:
        if arg is not None:
            return arg


def path_matches_patterns(path: PosixPath, patterns: Iterable[str]) -> bool:
    for ignore_pattern in patterns:
        if path.match(ignore_pattern):
            return True
    return False
