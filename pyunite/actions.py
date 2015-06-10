import vim
import funcy as fn

from .pure import *


def send_to_cmdline(string):
    # Paste current candidate into the bottom command line
    pass

common_actions = dict(
    nop = lambda _: None,
    send_to_cmdline = lambda x: vim.eval('feedkeys("' + escape_quote(x) + '")')
)

def tab_open(string):
    pass

def window_open(string):
    pass

def split_open(string):
    pass

def vsplit_open(string):
    pass

openable_actions = fn.merge(common_actions, dict(
    tab_open = tab_open,
    window_open = window_open,
    split_open = split_open,
    vsplit_open = vsplit_open,
))

def read(string):
    pass

def rename(string):
    pass

def remove(string):
    pass

def shell_cmd(string):
    # Run shell command on file
    pass

file_actions = fn.merge(openable_actions, dict(
    read = read,
    rename = rename,
    remove = remove,
    shell_cmd = shell_cmd,
))

def cd(string):
    pass

def lcd(string):
    pass

def run_pyunite(string):
    # Run PyUnite command with directory as current directory
    pass

directory_actions = fn.merge(file_actions, dict(
    cd = cd,
    lcd = lcd,
    run_pyunite = run_pyunite,
))

def run_ex(string):
    pass

def buf_rename(string):
    pass

def buf_remove(string):
    pass

def preview(string):
    pass

buffer_actions = fn.merge(directory_actions, dict(
    run_ex = run_ex,
    rename = buf_rename,
    remove = buf_remove,
    preview = preview,
))
