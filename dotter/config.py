from __future__ import annotations, absolute_import
from typing import Union, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass

import json
import os

from pathlib import PosixPath

# import dacite
# from dacite import from_dict

from .sync_plan import LogicalSyncPlan
from .utils import coalesce, path_matches_patterns, typecast, typecast_json_file

CONFIG_NAME = "dot.conf.json"
CONFIG_PATH = os.getenv("DOTTER_CONFIG_ROOT", "~/.config/dotter")

CONFIG_STANDARD = {
    "defaults": {
        "root": "~/",

        "add_dot": True,
        "use_contents": True,

        "link_mode": "recursive_link",
        "recursive_modifiers": {
            "link": ".xlink",
            "touch": ".xtouch",
            "copy": ".xcopy"
        },
        "ignore": [
            "*/.*",
            "*/.*/*",
        ]
    },
}

CONFIG_STANDARD_DEFAULTS = CONFIG_STANDARD.get("defaults")

class ConfigLinkMode(Enum):
    RLINK = "recursive_link"
    LINK = "link"
    RCOPY = "recursive_copy"
    COPY = "copy"
    TOUCH = "touch"

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"M({self.value})"

    def is_recursive(self):
        if self in [self.RLINK, self.RCOPY]:
            return True
        return False

    def unrecurse(self):
        return {
            self.RCOPY: self.COPY,
            self.RLINK: self.LINK,
        }.get(self, self)


@dataclass
class ConfigPatternSetting:
    root: Union[str, PosixPath] = None
    add_dot: bool = None
    use_contents: bool = None
    link_mode: ConfigLinkMode = None
    ignore: List[str] = None
    recursive_modifiers: Dict[ConfigLinkMode, str] = None

    def __post_init__(self):
        if self.root is not None:
            self.root = PosixPath(self.root).expanduser().resolve()

    def merge(self, override) -> ConfigPatternSetting:
        if override is None:
            return self
        return ConfigPatternSetting(
            root=coalesce(override.root, self.root),
            add_dot=coalesce(override.add_dot, self.add_dot),
            use_contents=coalesce(override.use_contents, self.use_contents),
            link_mode=coalesce(override.link_mode, self.link_mode),
            ignore=coalesce(override.ignore, self.ignore),
            recursive_modifiers=coalesce(override.recursive_modifiers, self.recursive_modifiers),
        )


@dataclass
class ConfigCategory:
    defaults: ConfigPatternSetting = None
    topics: Dict[str, ConfigPatternSetting] = None
    disabled: List[str] = None

    _root: PosixPath = None

    @property
    def root(self) -> PosixPath:
        return self._root

    @root.setter
    def root(self, path: PosixPath):
        self._root = path

    def __post_init__(self):
        if self.defaults is None:
            self.defaults = ConfigPatternSetting()
        if self.topics is None:
            self.topics = {}
        if self.disabled is None:
            self.disabled = []

    def merge_defaults(self):
        defaults = typecast(CONFIG_STANDARD_DEFAULTS, ConfigPatternSetting)
        self.defaults = defaults.merge(self.defaults)

    def merge_topics(self):
        for topic, override in self.topics.items():
            self.topics[topic] = self.defaults.merge(override)


@dataclass
class Config:
    config: ConfigCategory

    @staticmethod
    def root():
        return PosixPath(os.path.normpath(CONFIG_PATH)).expanduser()

    @staticmethod
    def from_dict(d: dict):
        return typecast(d, ConfigCategory)

    @staticmethod
    def categories():
        config_root = Config.root()
        return [
            p.relative_to(config_root)
            for p in config_root.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ]

    @staticmethod
    def load(category: str = None) -> Optional[Config]:
        config_root_path = Config.root()
        config_category_path = config_root_path.joinpath(category)
        config_file_path = config_category_path.joinpath(CONFIG_NAME)

        config_data = typecast_json_file(config_file_path, ConfigCategory, ConfigCategory())

        config_data.root = config_category_path
        config_data.merge_defaults()

        for contents in config_category_path.iterdir():
            if not contents.is_dir():
                continue
            if contents.name.startswith("."):
                continue
            if contents.name not in config_data.topics:
                config_data.topics[contents.name] = ConfigPatternSetting()

        config_data.merge_topics()

        conf = Config(
            config=config_data,
        )

        return conf


def compute_operations(category: Config) -> Dict[str, List[LogicalSyncPlan]]:
    ops: Dict[str, List[LogicalSyncPlan]] = {}
    for topic, topic_config in category.config.topics.items():
        config_topic_path = category.config.root.joinpath(topic)

        if not config_topic_path.exists():
            continue

        # Do we use contents of the folder?
        if topic_config.use_contents:
            # If we do then loop over all dirs
            link_items = list(config_topic_path.iterdir())
        else:
            # If we dont then only visit the toplevel dir.
            link_items = [config_topic_path]

        ops[topic] = compute_topic_operations(link_items, topic_config)
    return ops


def compute_topic_operations(link_items: List[PosixPath], link_config: ConfigPatternSetting):
    topic_ops: List[LogicalSyncPlan] = []

    for link_item in link_items:
        op_type, src_path, dst_path = _determine_operation(
            link_config, link_item.parent, link_item,
        )

        # Recursive link/copy mode is the most involved
        # - Find all recursive link modifiers in paths under link_item and adjust their link_mode.
        if op_type.is_recursive():
            # Break up paths by simple operations:
            link_paths = link_item.glob("**/*")
            link_paths = filter(lambda p: not path_matches_patterns(p, link_config.ignore), link_paths)

            seen_prefixes: Set[str] = set()
            for link_path in link_paths:
                op_type_switch, src_path, dst_path = _determine_operation(
                    link_config, link_item.parent, link_path,
                )

                if str(src_path) in seen_prefixes:
                    continue
                if src_path.is_dir() and op_type == op_type_switch:
                    continue

                seen_prefixes.add(str(src_path))

                topic_ops.append(LogicalSyncPlan(
                    type=op_type_switch,
                    src_path=src_path,
                    dst_path=dst_path,
                ))
        else:
            # Simple case, link item is directly linked, copied or touched.
            topic_ops.append(LogicalSyncPlan(
                type=op_type,
                src_path=src_path,
                dst_path=dst_path,
            ))

    return topic_ops


def _determine_operation(link_config: ConfigPatternSetting, link_root_path: PosixPath, link_path: PosixPath):
    op_type, prefix_path, src_path, suffix = _split_by_modifiers(str(link_path), link_config.recursive_modifiers)
    op_type = coalesce(op_type, link_config.link_mode)

    if op_type.is_recursive() and not link_path.is_dir():
        op_type = op_type.unrecurse()

    link_path = PosixPath(src_path)
    link_prefix_path = PosixPath(prefix_path)

    src_path = link_path
    dst_path = _rename_path(link_prefix_path, link_root_path, link_config.root, link_config.add_dot)

    return op_type, src_path, dst_path,


def _rename_path(path: PosixPath, base_path: PosixPath, new_base_path: PosixPath, add_dot: bool):
    rel_path = path.relative_to(base_path)
    if add_dot:
        rel_path = PosixPath("." + str(rel_path))
    return new_base_path.joinpath(rel_path)


def _split_by_modifiers(path: str, modifiers: Dict[ConfigLinkMode, str]) -> (ConfigLinkMode, str, str, str):
    (rext, prefix_path, src_path, suffix) = (None, path, path, "")
    for ext_name, ext in modifiers.items():
        idx = path.find(ext)
        if idx > 0:
            rext = ext_name
            prefix_path = path[0:idx]
            src_path = path[0:idx + len(ext)]
            suffix = path[idx + len(ext):]
    return rext, prefix_path, src_path, suffix
