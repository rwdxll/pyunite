import vim
import funcy as fn
from os import devnull, getcwd
from os.path import expanduser
from subprocess import Popen, PIPE, check_output
from pathlib import Path

from ..core import command_output


import timeit
def get_candidates(*args):
    cwd = str(Path(expanduser(args[0])).resolve()) if len(args) else getcwd()
    return Popen(['locate', cwd], stdout=PIPE).communicate()[0].split('\n')


def set_syntax():
    vim.command('syntax match locate_source_name /^locate/ contained')
    vim.command('syntax region locate oneline keepend start=/^locate/ end=/$/ contains=locate_.*')
    vim.command('highlight default link locate_source_name Comment')
