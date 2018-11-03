#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os
import logging
import argparse

from collections import OrderedDict

from .commander import Commander
from .utils import list_dir
from .sysops import SysOps
from .config import CatConfig


log = logging.getLogger("(root)")
log.addHandler(logging.StreamHandler(stream=sys.stderr))
log.setLevel("DEBUG")


class DotterScript(Commander):
    DEFAULT_CONF_DIR = os.path.expanduser("~/.groundzero/dotfiles")
    DEFAULT_ROOT = os.path.expanduser("~")

    def _global__args(self, parser):
        parser.add_argument('--root', dest='_root_dir', default=self.DEFAULT_ROOT,
                            help='Alternative root location (for testing configuration)')
        parser.add_argument('--conf-dir', dest='_conf_dir', default=self.DEFAULT_CONF_DIR,
                            help='Alternative configuration location (for testing configuration)')

    def _cmd__link__args(self, sparser):
        self._global__args(sparser)
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

    def _cmd__link(self, parser, args):
        dops = DotterOps(args.do_dry_run, args.do_force, args.do_backup)

        category, conf_dir, root_dir = self.get_config(args, parser)

        available_categories = map(
            lambda e: os.path.basename(e),
            list_dir(conf_dir, fullpath=True, select=os.path.isdir)
        )

        if category not in available_categories:
            parser.error("Category ({}) does not exist".format(category))

        selected_topic = args.topic
        category_ops = dops.Process_Category(conf_dir, category, root_dir=root_dir)
        if selected_topic:
            if selected_topic not in category_ops.keys():
                parser.error("Topic ({}) does not exist".format(selected_topic))
            category_ops = {selected_topic: category_ops[selected_topic]}

        dops.Apply_Category_Ops(category_ops)

    def _cmd__query__args(self, sparser):
        self._global__args(sparser)
        g = sparser.add_mutually_exclusive_group(required=True)
        g.add_argument('--list', action='store_true',
                       help='list topics and categories')
        g.add_argument('--list-target', action='store_true',
                       help='list destinations')
        g.add_argument('--list-source', action='store_true',
                       help='list destinations')
        g.add_argument('--list-all', action='store_true',
                       help='list destinations')

        g.add_argument('--list-diff', action='store_true',
                       help='list destinations')

        sparser.add_argument('-c', dest='category', default='common',
                             help='Specify a category to sync (defaults to common)')
        sparser.add_argument('-t', dest='topic',
                             help='Specify a topic to sync (inside a category)')

    def _cmd__query(self, parser, args):
        dops = DotterOps()
        category, conf_dir, root_dir = self.get_config(args, parser)

        available_categories = map(
            lambda e: os.path.basename(e),
            list_dir(conf_dir, fullpath=True, select=os.path.isdir)
        )

        def get_ops(selected_topic=None):
            category_ops = dops.Process_Category(conf_dir, category, root_dir=root_dir)
            if selected_topic:
                if selected_topic not in category_ops.keys():
                    parser.error("Topic ({}) does not exist".format(selected_topic))
                category_ops = {selected_topic: category_ops[selected_topic]}
            return category_ops

        if args.list:
            for category in available_categories:
                print("# [{}]".format(category))
                topics = list(list_dir(os.path.join(conf_dir, category), select=os.path.isdir))
                for topic in topics:
                    print("{}".format(topic))

        elif args.list_target:
            for topic, ops in get_ops(args.topic).items():
                print("# [{}]".format(topic))
                for op, files in ops.items():
                    print("#   ({})".format(op))
                    for src, des in files:
                        print("'{}'".format(des))

        elif args.list_source:
            for topic, ops in get_ops(args.topic).items():
                print("# [{}]".format(topic))
                for op, files in ops.items():
                    print("#   ({})".format(op))
                    for src, des in files:
                        print("'{}'".format(src))

        elif args.list_all:
            for topic, ops in get_ops(args.topic).items():
                print("# [{}]".format(topic))
                for op, files in ops.items():
                    print("#   ({})".format(op))
                    for src, des in files:
                        print("'{}' '{}'".format(src, des))

    def get_config(self, args, parser):
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


class DotterOps(object):
    DEFAULT_CONF_NAME="dot.json"

    def __init__(self, dry_run=False, force=False, backup=False):
        self.sysops = SysOps(dry_run=dry_run, force=force, backup=backup)

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

    def Process_Category(self, conf_dir, category, root_dir=None):
        category_dir = os.path.join(conf_dir, category)

        # Initialise the category configuration
        category_conf = CatConfig([{
            CatConfig.KEY_ROOT_PATH: root_dir,
            CatConfig.KEY_CATEGORY_PATH: category_dir,
        }])

        category_conf_file = os.path.join(category_dir, self.DEFAULT_CONF_NAME)
        if os.path.exists(category_conf_file) and os.path.isfile(category_conf_file):
            try:
                category_conf_ext = json.load(open(category_conf_file))
            except Exception:
                raise RuntimeError("Can not open or parse category configuration {}".format(category_conf_file))
            category_conf = category_conf.override([category_conf_ext])

        return self.Process_Category_Conf(category_conf)

    def Process_Category_Conf(self, category_conf):
        category_dir = category_conf.category_path

        topics = filter(
            lambda path: not category_conf.should_ignore_topic(path),
            list_dir(category_dir, select=os.path.isdir)
        )

        topic_confs = OrderedDict()
        for topic in topics:
            tconf = self.Process_Topic_Conf(category_conf, topic)
            topic_confs[topic] = tconf
        return topic_confs

    def Process_Topic_Conf(self, conf, topic):
        topic_conf = conf.get_topic_config(topic)
        topic_dir = os.path.join(topic_conf.category_path, topic)

        paths = []
        for (dirpath, dirnames, filenames) in os.walk(topic_dir):
            fpath = lambda x: os.path.join(dirpath, x)
            paths.extend(map(fpath, filenames))

        return self._sort_by_operation(paths, topic_conf)

    def _sort_by_operation(self, paths, conf):
        out = {}
        for path in paths:
            mode, src_path, des_path = conf.get_copy_mode(path)
            if not conf.should_ignore_file(src_path):
                o = out.get(mode, set())
                o.add((src_path, des_path))
                out[mode] = o
        return {k:sorted(v) for k,v in out.items()}


def main():
    parser = argparse.ArgumentParser(prog='dotter', description='dotfile linker')

    script = DotterScript()
    script.register_args(parser)

    try:
        return script.run(parser, parser.parse_args())
    except KeyboardInterrupt:
        return 1
    except Exception as e:
        # parser.error(str(e))
        # return 1
        raise


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
