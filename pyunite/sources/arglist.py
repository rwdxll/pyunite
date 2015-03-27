import vim
import re
import funcy as fn

from ..helpers import command_output


def gather_candidates():
    return fn.compact(re.split('\s+', command_output('args')))
