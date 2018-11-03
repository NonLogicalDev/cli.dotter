import shutil
import logging
import os

from .utils import yes_no_prompt, PP


class SysOps:
    log = logging.getLogger("SysOps")

    def __init__(self, dry_run=True, force=False, backup=False):
        self.log.debug("[INIT] Args: [dry_run: {}, force: {}, backup: {}]".format(dry_run, force, backup))

        self.dry_run = dry_run
        self.force = force
        self.backup = backup

    def ensure_folder(self, path, force=False):
        if not os.path.isdir(path):
            self.ensure_folder(os.path.dirname(path))

            PP.yellow("FOLDER : {}".format(path))
            if not self.dry_run:
                try:
                    os.mkdir(path)
                except FileExistsError as e:
                    if self.force and yes_no_prompt("Should replace file {} with folder?".format(path)):
                        os.remove(path)
                        os.mkdir(path)
                    else:
                        raise RuntimeError("Can not create {}".format(e.filename))

    def touch(self, src, dest, force=None):
        if force is None:
            force = self.force
        self.ensure_folder(os.path.dirname(dest), force=force)

        if os.path.exists(dest) or os.path.islink(dest):
            PP.green("TOCH[E]: {} -> {}".format(src, dest))
            return

        PP.yellow("TOCH   : {} -> {} (force:{})".format(src, dest, force))
        if not self.dry_run:
            shutil.copy(src, dest)

    def copy(self, src, dest, force=None):

        if force is None:
            force = self.force
        self.ensure_folder(os.path.dirname(dest), force=force)

        if os.path.exists(dest) or os.path.islink(dest):
            diff_code = os.popen("diff -q '{}' '{}'".format(src, dest)).close()

            if diff_code is None:
                PP.green("[E]COPY: {} -> {}".format(src, dest))
                return
            elif self.force and yes_no_prompt("Replace {} with {}?".format(src, dest)):
                PP.red("     RM: {}".format(src, dest))
                os.remove(dest)
            else:
                PP.green("[D]COPY: {} :: {}".format(src, dest))
                return

        PP.yellow("COPY   : {} -> {} (force:{})".format(src, dest, force))
        if not self.dry_run:
            shutil.copy(src, dest)

    def link(self, src, dest, force=None):
        if force is None:
            force = self.force
        self.ensure_folder(os.path.dirname(dest), force=force)

        if os.path.exists(dest) or os.path.islink(dest):
            if os.path.realpath(dest) == os.path.realpath(src):
                PP.green("[E]LINK: {} -> {}".format(src, dest))
                return
            elif self.force and yes_no_prompt("Replace {} with {}?".format(src, dest)):
                PP.red("     RM: {}".format(src, dest))
                os.remove(dest)
            else:
                PP.blue("[D]LINK: {} :: {}".format(src, dest))
                return
        else:
            print("WFT", dest)

        PP.yellow("   LINK: {} -> {} (force:{})".format(src, dest, force))
        if not self.dry_run:
            os.symlink(src, dest)

