import vim
import re
import funcy as fn

from ..core import command_output


def get_candidates(*source_args):
    return fn.compact(re.split('\s+', command_output('args')))


def set_syntax():
    vim.command('syntax match arglist_source_name /^arglist/ contained')
    vim.command('syntax region arglist oneline keepend start=/^arglist/ end=/$/ contains=arglist_.*')
    vim.command('highlight default link arglist_source_name Comment')
