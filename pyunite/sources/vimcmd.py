import vim

from ..core import command_output, icompact
from ..actions import common_actions
from ..variables import candidate


def get_candidates(*args):
    lines = icompact(command_output(args[0]).split('\n'))
    return map(lambda x: candidate._replace(filterable=x), lines)


actions = common_actions
default_action = actions['nop']


def actionable_string(action, candidate):
    return candidate.filterable


def syntaxes():
    return ['silent! syntax include @Vim syntax/vim.vim']


def highlights():
    return []
