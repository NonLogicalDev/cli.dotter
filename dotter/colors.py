HEADER = '\033[95m'

BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'

BOLD = '\033[1m'
UNDERLINE = '\033[4m'

ENDC = '\033[0m'


def red(*s):
    return RED + str(" ".join(s)) + ENDC

def green(*s):
    return GREEN + str(" ".join(s)) + ENDC

def yellow(*s):
    return YELLOW + str(" ".join(s)) + ENDC

def blue(*s):
    return BLUE + str(" ".join(s)) + ENDC
