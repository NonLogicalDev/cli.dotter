import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field
from pydantic.functional_serializers import PlainSerializer
from pydantic.functional_validators import PlainValidator

from dotter.utils import coalesce


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )


CONFIG_NAME = "dot.conf.json"
CONFIG_PATH = os.getenv("DOTTER_CONFIG_ROOT", "~/.config/dotter")

def _default_root():
    return "~/"

def _default_add_dot():
    return False

def _default_link_whole_dir():
    return False

def _default_link_mode():
    return ConfigLinkMode.RLINK

def _default_recursive_modifiers():
    return {
        ConfigLinkMode.LINK: ".xlink",
        ConfigLinkMode.TOUCH: ".xtouch",
        ConfigLinkMode.COPY: ".xcopy",
    }

class DotterRepo(BaseModel):
    root: Path

    @staticmethod
    def shared():
        return DotterRepo(root=Path(CONFIG_PATH).expanduser().resolve())

    def category_list(self):
        return [
            str(p.relative_to(self.root))
            for p in self.root.iterdir()
            if p.is_dir() and not p.name.startswith(".") and not p.name.startswith("__")
        ]

    def category_load(self, category_name: str) -> 'Optional[ConfigCategory]':
        config_category_path = self.root / category_name
        if not config_category_path.is_dir():
            return None

        config_category_file = config_category_path / CONFIG_NAME
        if not config_category_file.is_file():
            return None

        config_data = ConfigCategory.load_from_file(config_category_path, config_category_file)
        return config_data


class ConfigLinkMode(Enum):
    RLINK = "recursive_link"
    LINK = "link"
    RCOPY = "recursive_copy"
    COPY = "copy"
    TOUCH = "touch"

    def __str__(self):
        return str(self.value)

    def is_recursive(self):
        if self in [self.RLINK, self.RCOPY]:
            return True
        return False

    def unrecurse(self):
        return {
            self.RCOPY: self.COPY,
            self.RLINK: self.LINK,
        }.get(self, self)



ConfigPath = Annotated[
    Path,
    PlainSerializer(lambda v: str(v)),
    PlainValidator(lambda v: Path(v).expanduser().resolve() if v != None else None)
]


class ConfigPatternSetting(BaseModel):
    root: ConfigPath = \
        Field(default_factory=_default_root, validate_default=True)

    add_dot: Optional[bool] = \
        Field(default_factory=_default_add_dot, validate_default=True)

    link_mode: Optional[ConfigLinkMode] = \
        Field(default_factory=_default_link_mode,validate_default=True)

    link_whole_dir: Optional[bool] = \
        Field(default_factory=_default_link_whole_dir, validate_default=True)

    ignore: Optional[List[str]] = \
        Field(default_factory=list, validate_default=True)

    recursive_modifiers: Optional[Dict[ConfigLinkMode, str]] = \
        Field(default_factory=dict, validate_default=True)

    @classmethod
    def merge(cls, a, b) -> 'ConfigPatternSetting':
        if b is None:
            return a

        return ConfigPatternSetting(
            root=coalesce(b.root, a.root),
            add_dot=coalesce(b.add_dot, a.add_dot),
            link_mode=coalesce(b.link_mode, a.link_mode),
            link_whole_dir=coalesce(b.link_whole_dir, a.link_whole_dir),
            ignore=coalesce(b.ignore, a.ignore),
            recursive_modifiers=coalesce(b.recursive_modifiers, a.recursive_modifiers),
        )


class ConfigCategory(BaseModel):
    root: Optional[Path] = None

    defaults: Optional[ConfigPatternSetting] = \
        Field(default_factory=ConfigPatternSetting, validate_default=True)

    topics: Optional[Dict[str, ConfigPatternSetting]] = \
        Field(default_factory=dict)

    disabled: Optional[List[str]] = \
        Field(default_factory=list)

    @staticmethod
    def load_from_file(root: Path, path: Path) -> 'ConfigCategory':
        cfg = ConfigCategory.model_validate_json(path.read_text())
        cfg.root = root
        return cfg

    def topic_list(self):
        return [
            str(p.relative_to(self.root))
            for p in self.root.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ]

    def topic_load(self, topic_name: str):
        topic_path = self.root / topic_name
        if not topic_path.is_dir():
            return (None, None)

        topic_config = self.defaults
        if topic_name in self.topics:
            topic_config = ConfigPatternSetting.merge(topic_config, self.topics[topic_name])

        return (topic_path, topic_config)
