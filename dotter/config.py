import os
import re
import json
import fnmatch

from .utils import common_path

class CatConfig():
    KEY_ROOT_PATH = '_root_path'
    KEY_CATEGORY_PATH = '_category_path'
    KEY_TOPIC_PATH = '_topic_path'

    DEFAULT_CATEGORY_CONFIG = {
        # '_root_path': None,
        # '_category_path': None,

        'disabled':  [],

        'dir_mode':  'id',
        'dot_mode':  'top_level',
        'copy_mode': 'rlink',

        'rlink_ext':  'xrlink',
        'link_ext':  'xlink',
        'copy_ext':  'xcopy',
        'touch_ext': 'xtouch',

        'ignore': ['.DS_Store', '*.bak'],

        'dirconf': {
            # Define directory specific configurations here
        }
    }

    CONF_DIR_MODES = {
        "id",    # -- the folder itself will end up in root
        "root",  # -- the contents of the folder will end up in root
    }

    CONF_COPY_MODES = {
        "copy",   # -- the entity will be copied.
        "link",   # -- the entity will be linked as is.
        "rlink",  # -- the entity will be recursively linked, (i.e. each file will get its own link).
        "touch",  # -- the entity will be only copied if it does not exist.
    }

    CONF_DOT_MODES = {
        "no_dot",     # -- will not prepend dot to files
        "top_level",  # -- will prepend dot only to the topmost level
    }

    @staticmethod
    def _copy_conf(conf):
        return json.loads(json.dumps(conf))

    def __init__(self, overrides=None):
        if overrides is None:
            overrides = list()

        self.config = self._copy_conf(self.DEFAULT_CATEGORY_CONFIG)
        if not isinstance(overrides, list):
            raise RuntimeError("override not iterable")

        for o in overrides:
            self._override(o)

    def _override(self, overrides=None):
        if overrides is None:
            overrides = dict()
        self.config.update(self._copy_conf(overrides))
        self.config.pop("#", None)
        self.__compile()
        return self

    # Properties

    @property
    def topic_path(self):
        return self.config.get(self.KEY_TOPIC_PATH, None)

    @property
    def root_path(self):
        return self.config.get(self.KEY_ROOT_PATH, None)

    @property
    def category_path(self):
        return self.config.get(self.KEY_CATEGORY_PATH, None)

    @property
    def exts(self):
        return {
            "link": self.config.get('link_ext'),
            "copy": self.config.get('copy_ext'),
            "touch": self.config.get('touch_ext'),
        }

    # Interface

    def override(self, overrides=[{}]):
        return CatConfig([self.config] + overrides)

    def get_topic_config(self, topic):
        topic_override = self.config.get('dirconf').get(topic, {})
        overriden_conf = self.override([
            topic_override,
            { self.KEY_TOPIC_PATH: os.path.join(self.category_path, topic) }
        ])

        overriden_conf.config.pop('dirconf', None)
        return overriden_conf

    def should_ignore_file(self, path):
        for ign_re in self.compiled_ignores:
            if re.compile(ign_re).search(path):
                return True
        return False

    def should_ignore_topic(self, path):
        if os.path.basename(path) in self.config.get('disabled', []):
            return True
        return False

    def get_copy_mode(self, path):
        copy_mode = self.config.get('copy_mode')
        dot_mode = self.config.get('dot_mode')
        dir_mode = self.config.get('dir_mode')

        des_mods = ""
        if dir_mode == 'id':
            des_mods = "{}/".format(os.path.basename(self.topic_path))
        if dot_mode == 'top_level':
            des_mods = ".{}".format(des_mods)

        src_prefix_path, src_suffix_path = common_path(self.topic_path, path)
        des_prefix_path, des_suffix_path = self.root_path, src_suffix_path

        change_mode_match = self.compiled_ext_re.match(src_suffix_path)
        if change_mode_match:
            base, ext, rpath = change_mode_match.groups()

            if rpath is None:
                rpath = ""
            else:
                rpath = "/{}".format(rpath)

            src_suffix_path = "{}.{}".format(base, ext)
            des_suffix_path = "{}".format(base)

            if ext == self.exts["link"]:
                copy_mode = 'link'
            elif ext == self.exts["copy"]:
                copy_mode = 'copy'
            elif ext == self.exts["touch"]:
                copy_mode = 'touch'
                src_suffix_path = "{}.{}{}".format(base, ext, rpath)
                des_suffix_path = "{}{}".format(base, rpath)

        src_path = os.path.join(src_prefix_path, src_suffix_path)
        des_path = os.path.join(des_prefix_path, "{}{}".format(des_mods, des_suffix_path))

        if os.path.isdir(src_path):
            if not src_path.endswith("/"):
                src_path = src_path + "/"
            if not des_path.endswith("/"):
                des_path = des_path + "/"
        elif copy_mode == 'rlink':
            # Change mode for files to link as opposed to recursive link.
            copy_mode = 'link'

        return (copy_mode, src_path, des_path)

    def __compile(self):
        self.compiled_ignores = []
        for ignore_pat in self.config.get('ignore', []):
            self.compiled_ignores.append(fnmatch.translate(ignore_pat))
        #self.compiled_ignores = map(re.compile, self.compiled_ignores)

        self.compiled_ext_re = re.compile(
            "(.*?)"         # Path name
            "\."            # .
            "({})"          # Extension
            "(?:/(.*))?$"   # Rest of the path after known extension
            "".format("|".join([
                self.config.get('rlink_ext'),
                self.config.get('link_ext'),
                self.config.get('copy_ext'),
                self.config.get('touch_ext'),
            ]))
        )
        return self

    def __str__(self):
        return json.dumps(self.config, indent=4)
