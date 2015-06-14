import vim
import re

from ..core import command_output, icompact
from ..actions import directory_actions
from ..variables import candidate


def get_candidates(*args):
    lines = icompact(re.split(r'\s+', command_output('args')))
    return map(lambda x: candidate._replace(filterable=x), lines)


actions = directory_actions
default_action = actions['window_open']


def actionable_string(action, candidate):
    return candidate.filterable


def syntaxes():
    return []


def highlights():
    return []
