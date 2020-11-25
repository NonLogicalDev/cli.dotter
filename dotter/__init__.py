from __future__ import annotations
from typing import Optional

from argparse import ArgumentParser
from dataclasses import asdict
from pprint import pprint

from .config import Config, compute_operations, LINK_MODE_COPY
from .sync_plan import SyncError
from .version import __version__


class App:
    @classmethod
    def run(cls, parser: ArgumentParser):
        cmd = parser.add_subparsers(title="command", dest="cmd")
        parser.set_defaults(run=App.print_help(parser))

        ##################################################
        # Version
        ##################################################

        version_cmd = cmd.add_parser(
            "version", help="print version and exit",
        )
        version_cmd.set_defaults(run=App.run_version)

        ##################################################
        # Link
        ##################################################

        link_cmd = cmd.add_parser(
            "link", help=f"link dotfiles from {Config.root()}",
            description=f"links files into the home directory."
        )
        link_cmd.set_defaults(run=App.run_link)

        link_cmd.add_argument(
            '-c', dest='category', default='common',
            help='specify a category to sync (defaults to common)'
        )
        link_cmd.add_argument(
            '-t', dest='topic', default=None,
             help='specify a topic to sync (inside a category)'
        )
        link_cmd.add_argument(
            '-f', dest='force', action='store_true',
             help='Force execution'
        )
        link_cmd.add_argument(
            '-d', dest='dry_run', action='store_true',
            help='dry run current setup'
        )
        link_cmd.add_argument(
            '-b', dest='backup', action='store_false', default=True,
             help='backup files and place new ones in place, appends ".backup"'
        )

        ##################################################
        # Config
        ##################################################

        config_cmd = cmd.add_parser(
            "config", help="query configuration values",
            description="Query configuration values and sync plan."
        )
        config_cmd.set_defaults(run=App.print_help(config_cmd))

        config_subcommand = config_cmd.add_subparsers(title="command", dest="subcmd")

        ##################################################
        # Config/Root
        ##################################################

        config_root_cmd = config_subcommand.add_parser(
            "root", help="show root location"
        )
        config_root_cmd.set_defaults(run=App.run_config_root)

        ##################################################
        # Config/List
        ##################################################

        config_list_cmd = config_subcommand.add_parser(
            "list", help="list files and sync plan withing a category/topic"
        )
        config_list_cmd.set_defaults(run=App.run_config_list)

        config_list_cmd.add_argument("path", metavar="PATHS", nargs="?")

        ##################################################
        # Config/Dump
        ##################################################

        config_dump_cmd = config_subcommand.add_parser(
            "dump", help="dump parsed configuration for a particular category"
        )
        config_dump_cmd.set_defaults(run=App.run_config_dump)

        config_dump_cmd.add_argument("category", metavar="CATEGORY")

        ns = parser.parse_args()
        return ns.run(**vars(ns))

    @staticmethod
    def print_help(parser):
        return lambda **kwargs: parser.print_help()

    @staticmethod
    def run_version(**kwargs):
        print(__version__)

    @staticmethod
    def run_link(category: str, topic: str, dry_run: bool, backup: bool, force: bool, **kwargs):
        conf = Config.load(category)
        if conf is None:
            return
        for op_topic, ops in compute_operations(conf).items():
            if topic is not None and op_topic != topic:
                continue
            print(f":: Linking({op_topic})")
            for op in ops:
                for plan in op.reconcile():
                    if dry_run:
                        plan.print()
                    else:
                        plan.apply(force=force, backup=backup)

    @staticmethod
    def run_config_root(**kwargs):
        print(Config.root())
        return

    @staticmethod
    def run_config_list(path: Optional[str], **kwargs):
        if path is None:
            for category in Config.categories():
                print(f"Category({category}):")
                for topic in Config.load(category).config.topics:
                    print(f"  Topic({topic})")
            return

        components = path.split("/")
        while len(components) < 2:
            components.append("")

        category, topic, *suffix = components
        conf = Config.load(category)

        for op_topic, ops in compute_operations(conf).items():
            if topic != "" and op_topic != topic:
                continue
            print(f"Topic({op_topic}):")
            for op in ops:
                prefix_path = conf.config.root.joinpath(topic, *suffix)
                if op.src_path.is_relative_to(prefix_path):
                    print(f"  Path({op.src_path})")
                    print(f"    {op}")

            # compute_operations(conf).items()
            #
            # for f in filter(lambda p: p.is_file(), path.glob("**/*")):
            #     print(f"Path({f.relative_to(conf.config.root)})")

    @staticmethod
    def run_config_dump(category: str, **kwargs):
        conf = Config.load(category)
        pprint(asdict(conf), indent=2)