from __future__ import annotations
from typing import Dict, List

import shutil
import hashlib

from dataclasses import dataclass
from pathlib import PosixPath

from . import colors

class SyncError(RuntimeError):
    pass

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

    def print(self):
        if self.action == "create":
            print(colors.yellow(str(self)))
        elif self.action == "replace":
            print(colors.red(str(self)))

    def log(self, skip: bool = False):
        if skip:
            print(colors.blue("SKIPPING", str(self), "(force to apply)"))
        else:
            print(colors.yellow("APPLYING", str(self)))

    def apply(self, force: bool = False, backup: bool = True):
        if self.type == "dir":
            return self.apply_dir(force, backup)
        elif self.type == "touch":
            return self.apply_touch(force, backup)
        elif self.type == "link":
            return self.apply_link(force, backup)
        elif self.type == "copy":
            return self.apply_copy(force, backup)

    def apply_touch(self, force: bool, backup: bool):
        if self.src_path.is_file():
            self.log()
            self._copy_path(force=force, backup=backup)

    def apply_dir(self, force: bool, backup: bool):
        if self.action == "create":
            self.log()
            self.dst_path.mkdir(exist_ok=True)
        elif self.action == "replace":
            self.log(skip=not force)
            if force:
                self._backup_dest_path(backup)
                self.dst_path.mkdir(exist_ok=True)

    def apply_link(self, force: bool, backup: bool):
        if self.action == "create":
            self.log()
            self.dst_path.symlink_to(self.src_path)
        elif self.action == "replace":
            self.log(skip=not force)
            if force:
                self._backup_dest_path(backup)
                self.dst_path.symlink_to(self.src_path)

    def apply_copy(self, force: bool, backup: bool):
        if self.action == "create":
            self.log()
            self._copy_path(force=force, backup=backup)
        elif self.action == "replace":
            self.log(skip=not force)
            if force:
                self._backup_dest_path(backup)
                self._copy_path(force=force, backup=backup)

    def _backup_dest_path(self, backup: bool):
        if backup:
            dst_path_bak = PosixPath(str(self.dst_path) + ".bak")
            if dst_path_bak.exists():
                raise SyncError(f"file {dst_path_bak} already exists, clean up to continue")
            shutil.move(self.dst_path, dst_path_bak)
        else:
            self.dst_path.unlink(missing_ok=True)

    def _copy_path(self, force: bool, backup: bool):
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

    def reconcile(self) -> List[PhysicalSyncPlan]:
        if self.type == "touch":
            return self.reconcile_touch()
        elif self.type == "link":
            return self.reconcile_link()
        elif self.type == "copy":
            return self.reconcile_copy()
        return []

    def reconcile_dir(self, dst: PosixPath) -> List[PhysicalSyncPlan]:
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

    def reconcile_touch(self) -> List[PhysicalSyncPlan]:
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

    def reconcile_link(self) -> List[PhysicalSyncPlan]:
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
