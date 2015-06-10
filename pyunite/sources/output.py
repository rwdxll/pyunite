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


def set_syntax():
    vim.command('silent! syntax include @Vim syntax/vim.vim')
    vim.command('syntax match output_source_name /^output/ contained')
    vim.command('syntax region output oneline keepend start=/^output/ end=/$/ contains=@Vim,output_name')
    vim.command('highlight default link output_source_name Comment')
