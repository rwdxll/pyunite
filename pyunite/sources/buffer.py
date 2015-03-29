import vim
import funcy as fn

from ..core import command_output


def gather_candidates():
    return fn.compact(command_output('ls').split('\n'))
