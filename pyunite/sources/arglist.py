import vim
import re
import funcy as fn

from ..core import command_output, icompact
from ..actions import directory_actions
from ..variables import candidate


def get_candidates(*args):
    lines = icompact(re.split('\s+', command_output('args')))
    return map(lambda x: candidate._replace(filterable=x), lines)


actions = directory_actions
default_action = actions['window_open']


def actionable_string(action, candidate):
    return candidate.filterable


def set_syntax():
    vim.command('syntax match arglist_source_name /^arglist/ contained')
    vim.command('syntax region arglist oneline keepend start=/^arglist/ end=/$/ contains=arglist_.*')
    vim.command('highlight default link arglist_source_name Comment')
