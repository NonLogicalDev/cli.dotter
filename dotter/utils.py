from __future__ import annotations
from typing import Iterable, TypeVar, Dict, Type, Optional
from enum import Enum

import json
from pathlib import PosixPath

from dacite import from_dict, Config


T = TypeVar('T')


def typecast(d: Dict, data_class: Type[T]) -> T:
    return from_dict(data_class=data_class, data=d, config=Config(cast=[Enum]))


def typecast_json_file(path: PosixPath, data_class: Type[T], if_not_found: Optional[T] = None) -> Optional[T]:
    try:
        with open(path) as conf_fd:
            return typecast(json.load(conf_fd), data_class)
    except FileNotFoundError:
        return if_not_found


def coalesce(*args: T) -> T:
    for arg in args:
        if arg is not None:
            return arg


def path_matches_patterns(path: PosixPath, patterns: Iterable[str]) -> bool:
    for ignore_pattern in patterns:
        if path.match(ignore_pattern):
            return True
    return False
