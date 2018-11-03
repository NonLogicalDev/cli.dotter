import os
import re
import json

YN_PROMPT_RX = re.compile(r"(yes|no|y|n)")


class MyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class PP(object):
    HEADER = '\033[95m'

    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'

    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    ENDC = '\033[0m'

    @classmethod
    def red(cls, s):
        print(cls.RED + str(s) + cls.ENDC)

    @classmethod
    def green(cls, s):
        print(cls.GREEN + str(s) + cls.ENDC)

    @classmethod
    def yellow(cls, s):
        print(cls.YELLOW + str(s) + cls.ENDC)

    @classmethod
    def blue(cls, s):
        print(cls.BLUE + str(s) + cls.ENDC)


def jsdump(*args, **kwargs):
    kwargs.update(cls=MyJsonEncoder)
    return json.dumps(*args, **kwargs)


def common_path(path_a, path_b):
    cp = os.path.commonprefix([path_a, path_b])
    return cp, path_b.replace(cp, "")[1:]


def list_dir(path, fullpath=False, select=None):
    entries = os.listdir(path)
    if select:
        entries = filter(lambda e: select(os.path.join(path, e)), entries)
    if fullpath:
        entries = map(lambda e: os.path.join(path, e), entries)
    return entries


def yes_no_prompt(prompt):
    resp = None
    while resp is None:
        inp = input("{} (y/n): ".format(prompt))
        resp = YN_PROMPT_RX.match(inp)

    if resp.group(0) in ['y', 'yes']:
        return True
    else:
        return False
