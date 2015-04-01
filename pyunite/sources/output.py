import vim
import funcy as fn

from ..core import command_output


def get_candidates(*source_args):
    return fn.compact(command_output(source_args[0]).split('\n'))


def set_syntax():
    vim.command('silent! syntax include @Vim syntax/vim.vim')
    vim.command('syntax match output_source_name /^output/ contained')
    vim.command('syntax region output oneline keepend start=/^output/ end=/$/ contains=@Vim,output_name')
    vim.command('highlight default link output_source_name Comment')
