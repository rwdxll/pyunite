import vim
from os import getcwd
from os.path import expanduser
from subprocess import Popen, PIPE
from pathlib import Path

from ..core import icompact
from ..actions import directory_actions
from ..variables import candidate


def get_candidates(*args):
    cwd = str(Path(expanduser(args[0])).resolve()) if len(args) else getcwd()
    lines = icompact(Popen(['locate', cwd], stdout=PIPE).communicate()[0].split('\n'))
    return map(lambda x: candidate._replace(filterable=x), lines)


actions = directory_actions
default_action = actions['window_open']


def actionable_string(action, candidate):
    return candidate.filterable


def syntaxes():
    return []


def highlights():
    return []
