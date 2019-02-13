import shutil
import logging
import os
import stat
import errno

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
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        if self.force:
                            if yes_no_prompt("Should replace file {} with folder?".format(path)):
                                os.remove(path)
                                os.mkdir(path)
                        else:
                            raise RuntimeError("Can not create {}".format(e.filename))
                    else:
                        raise

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

        def do_copy():
            PP.yellow("COPY   : {} -> {} (force:{})".format(src, dest, force))
            if not self.dry_run:
                shutil.copy(src, dest)
        if os.path.exists(dest) or os.path.islink(dest):
            diff_code = os.popen("diff -q '{}' '{}'".format(src, dest)).close()

            if diff_code is None:
                PP.green("[E]COPY: {} -> {}".format(src, dest))
                return
            elif self.force:
                if yes_no_prompt("Replace {} with {}?".format(dest, src)):
                    PP.red("     RM: {}".format(src, dest))

                    try:
                        dest_mod = os.stat(dest).st_mode
                    except:
                        dest_mod = None

                    if dest_mod is not None and stat.S_ISDIR(dest_mod):
                        os.rmdir(dest)
                    else:
                        os.remove(dest)

                do_copy()
                return
            else:
                PP.green("[D]COPY: {} :: {}".format(src, dest))

                do_copy()
                return


    def link(self, src, dest, force=None):
        if force is None:
            force = self.force

        self.ensure_folder(os.path.dirname(dest), force=force)

        def do_link():
            PP.yellow("   LINK: {} -> {} (force:{})".format(src, dest, force))
            if not self.dry_run:
                os.symlink(src, dest)

        if os.path.exists(dest) or os.path.islink(dest):
            if os.path.realpath(dest) == os.path.realpath(src):
                PP.green("[E]LINK: {} -> {}".format(src, dest))
                return
            elif self.force:
                if yes_no_prompt("Replace {} with {}?".format(dest, src)):
                    PP.red("     RM: {}".format(src, dest))

                    try:
                        dest_mod = os.stat(dest).st_mode
                    except:
                        dest_mod = None

                    if dest_mod is not None and stat.S_ISDIR(dest_mod):
                        os.rmdir(dest)
                    else:
                        os.remove(dest)

                    do_link()
                    return
            else:
                PP.blue("[D]LINK: {} :: {}".format(src, dest))

                do_link()
                return
        else:
            print("WFT", dest)

