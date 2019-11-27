import json
import os
import sys
import argparse

from collections import OrderedDict
from itertools import chain

from .commander import Commander
from .utils import list_dir
from .sysops import SysOps
from .config import CatConfig


def resolve_path(path):
    while True:
        out_path = os.path.expanduser(os.path.expandvars(path))
        if out_path == path:
            break
        path = out_path
    return path


DEFAULT_CONF_NAME = "dot.json"
DEFAULT_CONF_DIR = os.getenv("DOTTER_CONFIG_ROOT", resolve_path("${HOME}/.config/dotter"))
DEFAULT_ROOT = os.getenv("DOTTER_OUTPUT_ROOT", resolve_path("${HOME}"))


class App(Commander):

    @staticmethod
    def _global__args(parser):
        parser.add_argument('--root', dest='_root_dir', default=DEFAULT_ROOT, metavar="ROOT_DIR",
                            help='Alternative root location (for testing configuration)')
        parser.add_argument('--conf-dir', dest='_conf_dir', default=DEFAULT_CONF_DIR, metavar="CONF_DIR",
                            help='Alternative configuration location (for testing configuration)')

    @staticmethod
    def get_config(parser, args):
        conf_dir = os.path.expandvars(os.path.expanduser(args._conf_dir))
        if not (os.path.exists(conf_dir) and os.path.isdir(conf_dir)):
            parser.error("Configuration dir is not found '{}'".format(conf_dir))
        category = args.category
        if args.category not in os.listdir(conf_dir):
            parser.error("Category {} is not found under '{}'".format(args.category, conf_dir))
        root_dir = os.path.expandvars(os.path.expanduser(args._root_dir))
        if not (os.path.exists(root_dir) and os.path.isdir(root_dir)):
            parser.error("Root dir is not found '{}'".format(conf_dir))
        return category, conf_dir, root_dir

    @classmethod
    def cmd__link__args(cls, sparser):
        cls._global__args(sparser)
        sparser.description = "links files into the home directory from the data root."

        sparser.add_argument('-c', dest='category', default='common',
                             help='Specify a category to sync (defaults to common)')
        sparser.add_argument('-t', dest='topic',
                             help='Specify a topic to sync (inside a category)')

        sparser.add_argument('-f', dest='do_force', action='store_true',
                             help='Force execution')
        sparser.add_argument('-d', dest='do_dry_run', action='store_true',
                             help='Dry run current setup')
        sparser.add_argument('-b', dest='do_backup', action='store_true',
                             help='Backup files and place new ones in place, appends ".backup"')

    @classmethod
    def cmd__link(cls, parser, args):
        category, conf_dir, root_dir = cls.get_config(parser, args)

        dops = DotterOps(
            root_dir=root_dir, conf_dir=conf_dir,
            dry_run=args.do_dry_run, force=args.do_force, backup=args.do_backup,
        )

        available_categories = dops.Get_Categories()
        if category not in available_categories:
            parser.error("Category ({}) does not exist".format(category))

        selected_topic = args.topic
        category_ops = dops.Process_Category(category)
        if selected_topic:
            if selected_topic not in category_ops.keys():
                parser.error("Topic ({}) does not exist".format(selected_topic))
            category_ops = {selected_topic: category_ops[selected_topic]}

        dops.Apply_Category_Ops(category_ops)

    @classmethod
    def cmd__query__args(cls, sparser: argparse.ArgumentParser):
        cls._global__args(sparser)
        sparser.description = "make various queries about the dotter repo."

        g = sparser.add_subparsers(help="sub commands", dest="action", required=True)
        actions = [
            g.add_parser('list', help='list topics and categories'),
            g.add_parser('list-target', help='list destinations'),
            g.add_parser('list-source', help='list destinations'),
            g.add_parser('list-all',  help='list destinations'),
            g.add_parser('list-diff',  help='list destinations'),
        ]
        for action in [sparser] + actions:
            action.add_argument('-c', dest='category', default='common',
                                 help='Specify a category to sync (defaults to common)')
            action.add_argument('-t', dest='topic',
                                 help='Specify a topic to sync (inside a category)')

    @classmethod
    def cmd__query(cls, parser, args):
        category, conf_dir, root_dir = cls.get_config(parser, args)
        dops = DotterOps(root_dir=root_dir, conf_dir=conf_dir)


        class ENC(json.JSONEncoder):
            def default(self, o):
                return o

        dumps = lambda o: json.dumps(o, cls=ENC, indent=True)
        available_categories = dops.Get_Categories()

        if args.action == "list":
            output = {}
            for category in available_categories:
                cd = []
                for topic, _ in dops.Process_Category(category).items():
                    cd += [topic]
                output[category] = cd
            print(dumps(output))

        elif args.action == "list-target":
            output = {}
            for category in available_categories:
                cd = {}
                for topic, ops in dops.Process_Category(category).items():
                    for op, files in ops.items():
                        for fr in files:
                            src, dst = fr
                            cd[topic] = cd.get(topic, []) + [dst]
                output[category] = cd
            print(dumps(output))

        elif args.action == "list-source":
            output = {}
            for category in available_categories:
                cd = {}
                for topic, ops in dops.Process_Category(category).items():
                    for op, files in ops.items():
                        for fr in files:
                            src, dst = fr
                            cd[topic] = cd.get(topic, []) + [dst]
                output[category] = cd
            print(dumps(output))

        elif args.action == "list-all":
            output = {}
            for category in available_categories:
                cd = {}
                for topic, ops in dops.Process_Category(category).items():
                    for op, files in ops.items():
                        for fr in files:
                            src, dst = fr
                            cd[topic] = cd.get(topic, []) + [{
                                "dst": dst, "src": src,
                            }]
                output[category] = cd
            print(dumps(output))

    def cmd__root__args(self, sparser: argparse.ArgumentParser):
        self._global__args(sparser)
        sparser.description = "returns the best guess for the location of the data root."

    @classmethod
    def cmd__root(cls, parser, args):
        print(DEFAULT_CONF_DIR)

    def cmd__config__args(self, sparser: argparse.ArgumentParser):
        self._global__args(sparser)
        sparser.description = "return a default configuration."

    @classmethod
    def cmd__config(cls, parser, args):
        json.dump(CatConfig([{
            "reference": {
                "copy-mode": {
                    "id":    "the folder itself will end up in root.",
                    "root": "the contents of the folder will end up in root.",
                },
                "dir-mode": {
                    "copy":   "the entity will be copied.",
                    "link":   "the entity will be linked as is.",
                    "rlink":  "the entity will be recursively linked, (i.e. each file will get its own link).",
                    "touch":  "the entity will be only copied if it does not exist.",
                },
                "dot-mode": {
                    "no_dot":    "will not prepend dot to files.",
                    "top_level": "will prepend dot only to the topmost level.",
                }
            },
            "dirconf": {
                "dirname0": {
                    "comment": "by default, "
                               "1: contents of folder will be recursively linked, "
                               "2: dot will be prepended to first level",
                },
                "dirname1": {
                    "comment": "folder will be linked recursively, with a dot prepended",
                    "dir_mode": "id"
                },
                "dirname2": {
                    "comment": "folder will be linked recursively, without a dot prepended",
                    "dir_mode": "id",
                    "dot_mode": "no_dot"
                },
                "dirname3": {
                    "comment": "folder will be linked copied, with a dot prepended",
                    "copy_mode": "copy",
                    "dir_mode": "id",
                },
            },
            "ignore": [
                ".DS_Store", "__pycache__/*", "*.swp",
            ],
        }]).config, sys.stdout, indent=True)


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
