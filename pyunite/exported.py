import vim
from copy import deepcopy
import funcy as fn
from itertools import imap
from operator import itemgetter as get

from . import defaults
from .decorators import export
from .helpers import *
from .exceptions import PyUniteException


@export()
def start(cmdline):
    start_unite(fn.merge(defaults.state, parse_cmdline(cmdline)))


@export()
def resume(cmdline):
    start_unite(parse_cmdline(cmdline))


@export()
def close(cmdline):
    start_unite(parse_cmdline(cmdline))


handlers = dict(
    # InsertEnter   = export()(on_insert_enter),
    # InsertLeave   = export()(on_insert_leave),
    # CursorHoldI   = export()(on_cursor_hold_i),
    # CursorMovedI  = export()(on_cursor_moved_i),
    # CursorMoved   = export()(on_cursor_moved),
    # CursorMovedI  = export()(on_cursor_moved),
    # BufHidden     = export()(on_buf_unload(expand'<afile>')),
    # BufUnload     = export()(on_buf_unload(expand'<afile>')),
    # WinEnter      = export()(on_bufwin_enter(bufnr(expand'<abuf>'))),
    # BufWinEnter   = export()(on_bufwin_enter(bufnr(expand'<abuf>'))),
    # InsertCharPre = export()(on_insert_char_pre),
    # TextChanged   = export()(on_text_changed),
)


def set_buffer_autocommands(buffer):
    vim.command('augroup plugin-pyunite')
    vim.command('autocmd! * <buffer=' + str(buffer.number) + '>')
    for event, handler in handlers:
        vim.command('autocmd ' + event + ' <buffer=' + str(buffer.number) + '> call s:' + handler.func_name + '()')
    vim.command('augroup END')


def set_buffer_mappings(buffer):
    pass


def set_window_options(window):
    options = window.options
    if vhas('cursorbind'):
        options['cursorbind'] = False
    if vhas('conceal'):
        options['conceallevel'] = 3
        options['concealcursor'] = 'niv'
    if vexists('+cursorcolumn'):
        options['cursorcolumn'] = False
    if vexists('+colorcolumn'):
        options['colorcolumn'] = 0
    if vexists('+relativenumber'):
        options['relativenumber'] = False
    options['cursorline'] = False
    options['foldcolumn'] = 0
    options['foldenable'] = False
    options['list'] = False
    options['number'] = False
    options['scrollbind'] = False
    options['spell'] = False


def set_buffer_options(buffer):
    buffer.options['bufhidden'] = 'wipe'
    buffer.options['buflisted'] = True
    buffer.options['buftype'] = 'nofile'
    buffer.options['completefunc'] = ''
    buffer.options['omnifunc'] = ''
    buffer.options['iskeyword'] += ',-,+,\\,!,~'
    buffer.options['matchpairs'] = re.sub('<:>,', '', buffer.options['matchpairs'])
    buffer.options['modeline'] = False
    buffer.options['modifiable'] = False
    buffer.options['readonly'] = False
    buffer.options['swapfile'] = False
    buffer.options['filetype'] = 'pyunite'


def make_pyunite_buffer(state):
    '''
    The current buffer is not changed in any way. This is done on purpose.
    '''
    buffer = make_buffer('pyunite[{}:{}]'.format(state['scope'], state['tabpage_or_window_number']))
    set_buffer_options(buffer)
    set_buffer_autocommands(buffer)
    set_buffer_mappings(buffer)
    # Vim uses garbage collection, so replacing the previous state is fine
    buffer.vars['pyunite_state'] = state
    return buffer


def populate_candidates(source):
    source['candidates'] = source_module(source).gather_candidates()


def formatted_candidates(source):
    return imap(lambda x: source['name'] + '  ' + x, source['candidates'])


def formatted_source_name(source):
    return source['name'] + '(' + str(len(source['candidates'])) + ')'


def formatted_source_names(sources):
    return imap(formatted_source_name, sources)


def set_buffer_contents(buffer, lines):
    buffer[:] = None
    buffer.append(lines, 0)


# The lambdas are here so that every time they are invoked the value os
# vim.current.* is actually current
scope_to_current = {
    'tabpage': lambda: vim.current.tabpage,
    'window': lambda: vim.current.window,
}


def buffer_is_reusable(state, buffer):
    # Obviously, we only reuse PyUnite's buffers
    if not is_pyunite_buffer(buffer):
        return False

    bufstate = buffer.vars['pyunite_state']

    # Only reuse buffers which have the same scope as the new state
    if bufstate['scope'] != state['scope']:
        return False

    # If the scopes are 'global' then we can reuse this buffer
    if bufstate['scope'] == state['scope'] == 'global':
        return True

    # Only reuse buffers which are either in the same tabpage or window
    # (depending on the scope)
    if bufstate['tabpage_or_window_number'] == scope_to_current[state['scope']]().number:
        return True

    return False


def start_unite(state):
    '''
    Open PyUnite window.

    Args:
        state (dict): Must be deepcopied to prevent modification of default state
    '''
    sources = state['sources']
    state['tabpage_or_window_number'] = scope_to_current[state['scope']]().number

    map(populate_candidates, sources)
    buffer = find(partial(buffer_is_reusable, state), vim.buffers) or make_pyunite_buffer(state)
    with scoped(buffer.options, modifiable=True):
        set_buffer_contents(buffer, fn.flatten(imap(formatted_candidates, sources)))

    window = window_with_buffer(buffer)
    # Later on we can refine this process (resize the window instead of
    # closing it, etc...)
    if window:
        close_window(window)
    print vim.eval('histget(":")')
    make_window(buffer)


def formatted_option(option):
    if isinstance(defaults.options[option], bool):
        return ['-' + re.sub('_', '-', option), '-no-' + re.sub('_', '-', option)]
    else:
        return ['-' + re.sub('_', '-', option) + '=']


@export()
def complete_options(arglead, cmdline, cursorpos):
    '''
    Provide a list of completion candidates for PyUnite* commands

    Args:
        arglead (str):    The word prefix being on which to complete upon
        cmdline (str):    Entire command line after the ':'
        cursorpos (str):  Cursor position in command line starting from 0. ':' character not counted

    Returns:
        list of strings: Completion candidates

    Notes:
        For more information, refer to the help for :command-completion-customlist
    '''
    formatted = fn.flatten(imap(formatted_option, defaults.options.keys()))
    return filter(lambda x: arglead in x, formatted)
