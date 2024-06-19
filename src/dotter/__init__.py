from pathlib import Path
import importlib.metadata
from typing import Dict, List, Set, Tuple

import click

#from .config import compute_operations, Config
from dotter.model import (ConfigCategory, ConfigLinkMode, ConfigPatternSetting,
                    DotterRepo)
from dotter.sync_plan import LogicalSyncPlan, PhysicalSyncPlan, compute_topic_operations

__version__ = importlib.metadata.version('dotter')

DOTTER_HELP = """
A dotfile linker.

This utility creates a link farm from a data root to users home directory.
It's intended use is to keep dotfiles neatly organized and separated by topics.
""".strip()


@click.group(
    help=DOTTER_HELP,
    context_settings=dict(help_option_names=['-h', '--help']),
)
def main():
    pass

@main.command(name='link', help="link dotfiles from root")
@click.option('-c', '--category', type=str, default='common', help='specify a category to sync', show_default=True)
@click.option('-t', '--topic', type=str, default="", help='specify a topic to sync (inside a category)')
@click.option('-f', '--force', is_flag=True, default=False, help='force execution of operations')
@click.option('-d', '--dry-run', is_flag=True, default=False, help='dry run current setup')
@click.option('-b/-B', 'backup', is_flag=True, default=True, help='backup files and place new ones in place, appends ".bak"')
@click.option('-v', '--verbose', is_flag=True, default=False, help='verbose output')
def main_link(category: str, topic: str, force: bool, dry_run: bool, backup: bool, verbose: bool):
    repo = DotterRepo.shared()
    cfg_category = repo.category_load(category)
    if cfg_category is None:
        raise click.ClickException(f"Category {category} not found in {repo.root}")

    topics_to_sync = cfg_category.topic_list()
    if len(topic) != 0:
        topics_to_sync = [topic]

    def __op_report(plan: PhysicalSyncPlan, needs_force: bool):
        mark = "   "
        arrow = "->"
        if plan.type == 'link':
            arrow = "<-"
        plan_s = f"[{plan.type}:{plan.action}] {plan.src_path} {arrow} {plan.dst_path}"

        if needs_force:
            msg = click.style(f"! {plan_s} (needs force)", fg='red')
        elif plan.action == 'remove':
            msg = click.style(f"- {plan_s}", fg='red')
        elif plan.action in ['create'] or plan.type == ['touch']:
            msg = click.style(f"+ {plan_s}", fg='green')

        click.echo(f"{mark}{msg}")

    def __sop_repot(plan: LogicalSyncPlan):
        mark = "   "
        arrow = "->"
        if plan.type == 'link':
            arrow = "<-"
        plan_s = f"[{plan.type}] {plan.src_path} {arrow} {plan.dst_path}"
        msg = click.style(f"* {plan_s}", fg='blue')
        if verbose:
            click.echo(f"{mark}{msg}")

    for topic_name in topics_to_sync:
        path_topic, cfg_topic = cfg_category.topic_load(topic_name)
        if cfg_topic is None:
            raise click.ClickException(f"Topic {topic_name} not found in {cfg_category.root}")

        print(f":: Linking({topic_name})")
        topic_plan = compute_topic_operations(path_topic, cfg_topic)
        for op in topic_plan:
            __sop_repot(op)
            for plan in op.reconcile():
                plan.apply(force=force, backup=True, dry_run=dry_run, report=__op_report)

@main.command(name='version', short_help="show version")
def main_version():
    click.echo(__version__)

@main.group(name='config', short_help="config related commands")
def main_config():
    pass

@main_config.command(name='root', short_help="print config root")
def config_root():
    click.echo(str(DotterRepo.shared().root))
    pass

@main_config.command(name='list', short_help="list configs")
@click.option('-p', '--path', type=str, default=None)
def config_list(path: str = None):
    repo = DotterRepo.shared()

    if path is None:
        for category in repo.category_list():
            print(f"Category({category}):")
            for topic in repo.category_load(category).topic_list():
                print(f"  Topic({topic})")
        return

    components = path.split("/")
    while len(components) < 2:
        components.append("")

    category, topic, *suffix = components
    conf = repo.category_load(category)

    for op_topic in conf.topic_list():
        print(f"Topic({op_topic}):")
        if topic != "" and op_topic != topic:
            continue
        topic_path, cfg_topic = conf.topic_load(op_topic)
        for op in compute_topic_operations(topic_path, cfg_topic):
            op_path = str(op.src_path.relative_to(repo.root))
            print(f"  Path({op_path})")
            print(f"    {op.type} :: {op.src_path} <> {op.dst_path}")

if __name__ == '__main__':
    main()
