import json
import os
import sys
import argparse

from .commander import Commander
from .config import CatConfig
from .dotterops import DotterOps
from .sysops import SysOps
from .utils import list_dir

from .settings.constants import DEFAULT_CONF_DIR, DEFAULT_ROOT

class App(Commander):

    @staticmethod
    def _global__args(parser: argparse.ArgumentParser):
        parser.formatter_class = argparse.RawTextHelpFormatter

        parser.description = "\n".join([
            "A dotfile linker.",
            "\n",
            "This utility creates a link farm from a data root to users home directory. ",
            "It's intended use is to keep dotfiles neatly organized and separated by topics.",
            "\n",
            "\n",
            "Following ENV variables control the default behaviour:",
            "DOTTER_CONFIG_ROOT: Configuration root (where dotfiles live).",
            "DOTTER_OUTPUT_ROOT: Output root where the files will be linked to.",
        ])

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
        sparser.description = "return an example configuration."

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
