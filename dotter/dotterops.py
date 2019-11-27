import json
import os
from collections import OrderedDict
from itertools import chain

from .sysops import SysOps
from .config import CatConfig
from .utils import list_dir
from .settings.constants import DEFAULT_CONF_NAME


class DotterOps(object):
    def __init__(self, root_dir=None, conf_dir=None, dry_run=False, force=False, backup=False):
        self.root_dir = root_dir
        self.conf_dir = conf_dir
        self.sysops = SysOps(dry_run=dry_run, force=force, backup=backup)

    def Get_Categories(self, fullpath=True):
        return filter(lambda e: not e.startswith("."), map(
            lambda e: os.path.basename(e),
            list_dir(self.conf_dir, fullpath=fullpath, select=os.path.isdir)
        ))

    def Apply_Category_Ops(self, ops):
        for topic, ops in ops.items():
            for op_type, op_files in ops.items():
                for src, des in op_files:
                    if op_type == 'copy':
                        self.sysops.copy(src, des)
                    elif op_type == 'link':
                        self.sysops.link(src, des)
                    elif op_type == 'touch':
                        self.sysops.touch(src, des)

    def Process_Category(self, category):
        category_dir = os.path.join(self.conf_dir, category)

        # Initialise the category configuration
        category_conf = CatConfig([{
            CatConfig.KEY_ROOT_PATH: self.root_dir,
            CatConfig.KEY_CATEGORY_PATH: category_dir,
        }])

        category_conf_file = os.path.join(category_dir, DEFAULT_CONF_NAME)
        if os.path.exists(category_conf_file) and os.path.isfile(category_conf_file):
            try:
                category_conf_ext = json.load(open(category_conf_file))
            except Exception:
                raise RuntimeError("Can not open or parse category configuration {}".format(category_conf_file))
            category_conf = category_conf.override([category_conf_ext])

        return self.Process_Category_Conf(category_conf)

    def Process_Category_Conf(self, conf):
        category_dir = conf.category_path

        topics = filter(
            lambda path: not conf.should_ignore_topic(path),
            list_dir(category_dir, select=os.path.isdir)
        )

        topic_confs = OrderedDict()
        for topic in topics:
            tconf = self.Process_Topic_Conf(conf, topic)
            topic_confs[topic] = tconf

        return topic_confs

    def Process_Topic_Conf(self, conf, topic):
        topic_conf = conf.get_topic_config(topic)
        topic_dir = os.path.join(topic_conf.category_path, topic)

        ops = {}
        prefixes = set()

        topic_entry = [(os.path.dirname(topic_dir), [topic_dir], [])]
        for (dirpath, dirnames, filenames) in chain(topic_entry, os.walk(topic_dir)):
            fpath = lambda x: os.path.join(dirpath, x)

            for path in map(fpath, chain(dirnames, filenames)):
                mode, src_path, des_path = topic_conf.get_copy_mode(path)

                skip = False
                for p in prefixes:
                    if src_path.startswith(p):
                        skip = True
                        break
                if skip:
                    continue

                if mode != "rlink":
                    prefixes.add(src_path)

                if not conf.should_ignore_file(path):
                    o = ops.get(mode, set())
                    o.add((src_path, des_path))
                    ops[mode] = o

        return {
            _type: sorted(_ops)
            for _type, _ops in ops.items()
        }

    # def _sort_by_operation(self, paths, conf):
    #     out = {}
    #     for path in paths:
    #         mode, src_path, des_path = conf.get_copy_mode(path)
    #         if not conf.should_ignore_file(src_path):
    #             o = out.get(mode, set())
    #             o.add((src_path, des_path))
    #             out[mode] = o
    #     return {k:sorted(v) for k,v in out.items()}
