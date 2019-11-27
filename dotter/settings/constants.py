import os

from dotter.utils import resolve_path

DEFAULT_CONF_NAME = "dot.json"
DEFAULT_CONF_DIR = os.getenv("DOTTER_CONFIG_ROOT", resolve_path("${HOME}/.config/dotter"))
DEFAULT_ROOT = os.getenv("DOTTER_OUTPUT_ROOT", resolve_path("${HOME}"))