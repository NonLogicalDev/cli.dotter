import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path, PosixPath
from typing import Callable, Dict, List, Tuple

from dotter.model import ConfigCategory, ConfigLinkMode, ConfigPatternSetting
from dotter.utils import coalesce, path_matches_patterns


class SyncError(RuntimeError):
    pass

@dataclass
class PhysicalSyncPlanApplyCtx:
    force: bool
    backup: bool
    dry_run: bool
    report: Callable


@dataclass
class PhysicalSyncPlan:
    type: str
    action: str
    src_path: PosixPath
    dst_path: PosixPath

    def __str__(self):
        if self.type == "link":
            return f"PLAN({self.type}.{self.action} {str(self.src_path)} <- {self.dst_path})"
        else:
            return f"PLAN({self.type}.{self.action} {str(self.src_path)} -> {self.dst_path})"

    def log(self, ctx: 'PhysicalSyncPlanApplyCtx', skip: bool = False):
        if ctx.report:
            ctx.report(plan=self, needs_force=skip)

    def apply(self, force: bool = False, backup: bool = True, dry_run: bool = False, report: Callable = lambda **kwargs: None):
        ctx = PhysicalSyncPlanApplyCtx(force, backup, dry_run, report)
        if ctx.dry_run:
            return self.log(ctx)

        if self.type == "dir":
            return self.apply_dir(ctx)
        elif self.type == "touch":
            return self.apply_touch(ctx)
        elif self.type == "link":
            return self.apply_link(ctx)
        elif self.type == "copy":
            return self.apply_copy(ctx)

    def apply_touch(self, ctx: 'PhysicalSyncPlanApplyCtx'):
        if self.src_path.is_file():
            self.log(ctx)
            self._copy_path(ctx)

    def apply_dir(self, ctx: 'PhysicalSyncPlanApplyCtx'):
        if self.action == "create":
            self.log(ctx)
            self.dst_path.mkdir(exist_ok=True)
        elif self.action == "replace":
            self.log(skip=not ctx.force)
            if ctx.force:
                self._backup_dest_path(ctx)
                self.dst_path.mkdir(exist_ok=True)

    def apply_link(self, ctx: 'PhysicalSyncPlanApplyCtx'):
        if self.action == "create":
            self.log(ctx)
            self.dst_path.symlink_to(self.src_path)
        elif self.action == "replace":
            self.log(ctx, skip=not ctx.force)
            if ctx.force:
                self._backup_dest_path(ctx)
                self.dst_path.symlink_to(self.src_path)

    def apply_copy(self, ctx: 'PhysicalSyncPlanApplyCtx'):
        if self.action == "create":
            self.log(ctx)
            self._copy_path(ctx)
        elif self.action == "replace":
            self.log(ctx, skip=not ctx.force)
            if ctx.force:
                self._backup_dest_path(ctx)
                self._copy_path(ctx)

    def _backup_dest_path(self, ctx: 'PhysicalSyncPlanApplyCtx'):
        if ctx.backup:
            dst_path_bak = PosixPath(str(self.dst_path) + ".bak")
            if dst_path_bak.exists():
                raise SyncError(f"file {dst_path_bak} already exists, clean up to continue")
            shutil.move(self.dst_path, dst_path_bak)
        else:
            self.dst_path.unlink(missing_ok=True)

    def _copy_path(self, ctx: 'PhysicalSyncPlanApplyCtx'):
        if self.src_path.is_file():
            shutil.copy2(self.src_path, self.dst_path)
        else:
            shutil.copytree(self.src_path, self.dst_path)


@dataclass
class LogicalSyncPlan:
    type: str
    src_path: PosixPath
    dst_path: PosixPath
    # debug: str = None

    def reconcile(self) -> 'List[PhysicalSyncPlan]':
        if self.type == "touch":
            return self.reconcile_touch()
        elif self.type == "link":
            return self.reconcile_link()
        elif self.type == "copy":
            return self.reconcile_copy()
        return []

    def reconcile_dir(self, dst: PosixPath) -> 'List[PhysicalSyncPlan]':
        ops = []
        for parent in reversed(dst.parents):
            if not parent.exists():
                ops.append(PhysicalSyncPlan(
                    type="dir", action="create",
                    dst_path=parent,
                    src_path=parent
                ))
            elif not parent.is_dir():
                ops.append(PhysicalSyncPlan(
                    type="dir", action="replace",
                    dst_path=parent,
                    src_path=parent
                ))
        return ops

    def reconcile_touch(self) -> 'List[PhysicalSyncPlan]':
        ops = []
        ops.extend(self.reconcile_dir(self.dst_path))

        dst_path_stat = None
        try:
            dst_path_stat = self.dst_path.lstat()
        except:
            pass

        if dst_path_stat is not None:
            # if dst_path exists in any form.
            return []

        ops.append(PhysicalSyncPlan(
            type="touch", action="create",
            src_path=self.src_path,
            dst_path=self.dst_path,
        ))
        return ops

    def reconcile_link(self) -> 'List[PhysicalSyncPlan]':
        ops = []
        ops.extend(self.reconcile_dir(self.dst_path))

        dst_path_stat = None
        try:
            dst_path_stat = self.dst_path.lstat()
        except:
            pass

        if dst_path_stat is None:
            # if dst_path does not exist.
            ops.append(PhysicalSyncPlan(
                type="link", action="create",
                src_path=self.src_path,
                dst_path=self.dst_path,
            ))
        elif not _check_link_points_to(self.dst_path, self.src_path):
            ops.append(PhysicalSyncPlan(
                type="link", action="replace",
                src_path=self.src_path,
                dst_path=self.dst_path,
            ))
        return ops

    def reconcile_copy(self):
        ops = []
        ops.extend(self.reconcile_dir(self.dst_path))

        if not self.dst_path.exists():
            ops.append(PhysicalSyncPlan(
                type="copy", action="create",
                src_path=self.src_path,
                dst_path=self.dst_path,
            ))
        elif not _check_paths_same_type(self.src_path, self.dst_path):
            ops.append(PhysicalSyncPlan(
                type="copy", action="replace",
                src_path=self.src_path,
                dst_path=self.dst_path,
            ))
        elif self.src_path.is_file():
            ops.append(PhysicalSyncPlan(
                type="copy", action="replace",
                src_path=self.src_path,
                dst_path=self.dst_path,
            ))
        elif self.src_path.is_dir():
            missing_files, existing_files = _get_missing_files(self.src_path, self.dst_path)
            for f in missing_files:
                dst_path = self.dst_path.joinpath(f)
                src_path = self.src_path.joinpath(f)
                ops.extend(self.reconcile_dir(dst_path))
                ops.append(PhysicalSyncPlan(
                    type="copy", action="create",
                    src_path=src_path,
                    dst_path=dst_path,
                ))
            for f in existing_files:
                dst_path = self.dst_path.joinpath(f)
                src_path = self.src_path.joinpath(f)
                if not _check_file_equal(src_path, dst_path):
                    ops.append(PhysicalSyncPlan(
                        type="copy", action="replace",
                        src_path=src_path,
                        dst_path=dst_path,
                    ))
        return ops

# ------------------------------------------------------------------------------

# MARK: Sync Plan Operations

def compute_topic_operations(topic_path: Path, link_config: 'ConfigPatternSetting'):
    topic_ops: List[LogicalSyncPlan] = []

    # Do we use contents of the folder?
    # If we dont then only visit the toplevel dir.
    link_items = [topic_path]
    if not link_config.link_whole_dir:
        # If we do then loop over all dirs
        link_items = list(topic_path.iterdir())

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
                    type=str(op_type_switch),
                    src_path=src_path,
                    dst_path=dst_path,
                ))
        else:
            # Simple case, link item is directly linked, copied or touched.
            topic_ops.append(LogicalSyncPlan(
                type=str(op_type),
                src_path=src_path,
                dst_path=dst_path,
            ))

    return topic_ops


def _determine_operation(link_config: 'ConfigPatternSetting', link_root_path: Path, link_path: Path):
    op_type, prefix_path, src_path, suffix = _split_by_modifiers(str(link_path), link_config.recursive_modifiers)
    op_type = coalesce(op_type, link_config.link_mode)

    if op_type.is_recursive() and not link_path.is_dir():
        op_type = op_type.unrecurse()

    link_path = Path(src_path)
    link_prefix_path = Path(prefix_path)

    src_path = link_path
    dst_path = _rename_path(link_prefix_path, link_root_path, link_config.root, link_config.add_dot)

    return op_type, src_path, dst_path,


def _rename_path(path: Path, base_path: Path, new_base_path: Path, add_dot: bool):
    rel_path = path.relative_to(base_path)
    if add_dot:
        rel_path = Path("." + str(rel_path))
    return new_base_path.joinpath(rel_path)


def _split_by_modifiers(path: str, modifiers: Dict[ConfigLinkMode, str]) -> Tuple[ConfigLinkMode, str, str, str]:
    (rext, prefix_path, src_path, suffix) = (None, path, path, "")
    for ext_name, ext in modifiers.items():
        idx = path.find(ext)
        if idx > 0:
            rext = ext_name
            prefix_path = path[0:idx]
            src_path = path[0:idx + len(ext)]
            suffix = path[idx + len(ext):]
    return rext, prefix_path, src_path, suffix


# ------------------------------------------------------------------------------

def _check_paths_same_type(a: PosixPath, b: PosixPath) -> bool:
    if a.is_file() and b.is_file():
        return True
    if a.is_dir() and b.is_dir():
        return True
    return False


def _check_link_points_to(src: PosixPath, dst: PosixPath) -> bool:
    if src.is_symlink() and src.resolve() == dst.resolve():
        return True
    return False


def _check_dir_equal(src: PosixPath, dst: PosixPath):
    missing_files, _ = _get_missing_files(src, dst)
    if len(missing_files) > 0:
        return False
    return True


def _check_file_equal(a: PosixPath, b: PosixPath):
    if not a.exists() or not b.exists():
        return False
    if not a.is_file() or not b.is_file():
        return False
    ha = hashlib.md5(open(a, 'rb').read()).hexdigest()
    hb = hashlib.md5(open(b, 'rb').read()).hexdigest()
    return ha == hb


def _get_missing_files(src: PosixPath, dst: PosixPath):
    subpath = lambda base: lambda p: p.relative_to(base)
    is_file = lambda p: p.is_file()

    src_files = set(map(subpath(src), filter(is_file, src.glob("**/*"))))
    dst_files = set(map(subpath(dst), filter(is_file, dst.glob("**/*"))))

    existing = dst_files.intersection(src_files)
    missing = src_files.difference(existing)

    return sorted(missing), sorted(existing)
