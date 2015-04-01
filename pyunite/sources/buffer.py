import vim
import funcy as fn

from ..core import command_output


def get_candidates(*source_args):
    return fn.compact(command_output('ls').split('\n'))


def set_syntax():
    vim.command('syntax match buffer_name /[^/ \[\]]\+\s/ contained')
    vim.command('syntax match buffer_prefix /\d\+\s\%(\S\+\)\?/ contained')
    vim.command('syntax match buffer_info /\[.\{-}\] / contained')
    vim.command('syntax match buffer_modified /\[.\{-}+\]/ contained')
    vim.command('syntax match buffer_nofile /\[nofile\]/ contained')
    vim.command('syntax match buffer_time /(.\{-}) / contained')
    vim.command('syntax match buffer_source_name /^buffer/ contained')
    vim.command('syntax region buffer oneline keepend start=/^buffer/ end=/$/ contains=buffer_.*')
    vim.command('highlight default link buffer_source_name Comment')
    vim.command('highlight default link buffer_name Function')
    vim.command('highlight default link buffer_prefix Constant')
    vim.command('highlight default link buffer_info PreProc')
    vim.command('highlight default link buffer_modified Statement')
    vim.command('highlight default link buffer_nofile Function')
    vim.command('highlight default link buffer_time Statement')
