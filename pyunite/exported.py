import vim
from uuid import uuid4 as uniqueid
from copy import deepcopy
import funcy as fn
from itertools import imap
from operator import itemgetter as get

from . import defaults
from .decorators import export
from .helpers import *


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


def set_buffer_autocommands(buf):
    vim.command('augroup plugin-pyunite')
    vim.command('autocmd! * <buffer=' + str(buf.number) + '>')
    for event, handler in handlers:
        vim.command('autocmd ' + event + ' <buffer=' + str(buf.number) + '> call s:' + handler.func_name + '()')
    vim.command('augroup END')


def set_buffer_mappings(buf):
    pass


def set_window_options(window):
    if vhas('cursorbind'):
        window.options['cursorbind'] = False
    if vhas('conceal'):
        window.options['conceallevel'] = 3
        window.options['concealcursor'] = 'niv'
    if vexists('+cursorcolumn'):
        window.options['cursorcolumn'] = False
    if vexists('+colorcolumn'):
        window.options['colorcolumn'] = ''
    if vexists('+relativenumber'):
        window.options['relativenumber'] = False
    window.options['cursorline'] = False
    window.options['foldcolumn'] = 0
    window.options['foldenable'] = False
    window.options['list'] = False
    window.options['number'] = False
    window.options['scrollbind'] = False
    window.options['spell'] = False


def set_buffer_options(buf):
    buf.options['bufhidden'] = 'wipe'
    buf.options['buflisted'] = True
    buf.options['buftype'] = 'nofile'
    buf.options['completefunc'] = ''
    buf.options['omnifunc'] = ''
    buf.options['iskeyword'] += ',-,+,\\,!,~'
    buf.options['matchpairs'] = re.sub('<:>,', '', buf.options['matchpairs'])
    buf.options['modeline'] = False
    buf.options['modifiable'] = False
    buf.options['readonly'] = False
    buf.options['swapfile'] = False
    buf.options['filetype'] = 'pyunite'


def set_buffer_state(state, buf):
    # Vim uses garbage collection, so replacing the previous state is fine
    buf.vars['pyunite_state'] = state


def set_buffer_contents(state, buf):
    with scoped(buf.options, modifiable=True):
        buf[:] = None
        content = fn.flatten(imap(formatted_candidates, state['sources']))
        buf.append(content, 0)


def make_pyunite_buffer(state):
    buf = make_buffer('pyunite:{}'.format(state['uid'][:7]))
    set_buffer_options(buf)
    set_buffer_autocommands(buf)
    set_buffer_mappings(buf)
    set_buffer_state(state, buf)
    set_buffer_contents(state, buf)
    return buf


def make_pyunite_window(state, buf):
    window = make_window(
        direction = state['direction'],
        size = state['size'],
        vsplit = state['vsplit'],
        buffer_name = buf.name,
    )
    set_window_options(window)
    return window


def populate_candidates(source):
    source['candidates'] = source_module(source).gather_candidates()


def formatted_candidates(source):
    return imap(lambda x: source['name'] + '  ' + x, source['candidates'])


def formatted_source_name(source):
    return source['name'] + '(' + str(len(source['candidates'])) + ')'


def formatted_source_names(sources):
    return imap(formatted_source_name, sources)


def sources_names(state):
    return map(get('name'), state['sources'])


def get_state(buf):
    return buf.vars['pyunite_state']


def find_pyunite_buffer(state):
    choosable = lambda x: is_pyunite_buffer(x) and state['scope'] == get_state(x)['scope']
    for buf in ifilter(choosable, vim.buffers):
        if sources_names(state) == sources_names(get_state(buf)):
            return buf
        if get_state(buf)['reusable']:
            set_buffer_state(state, buf)
            set_buffer_contents(state, buf)
            return buf
    return None
        

def start_unite(state):
    '''
    Open PyUnite window.

    Args:
        state (dict): Must be deepcopied to prevent modification of default state
    '''
    # TODO: Find better way of validating input
    assert state['scope'] in ['global', 'tab', 'window']
    assert state['direction'] in ['topleft', 'botright', 'leftabove', 'rightbelow']

    state['uid'] = str(uniqueid())

    map(populate_candidates, state['sources'])
    buf = find_pyunite_buffer(state) or make_pyunite_buffer(state)
    window = window_with_buffer(buf) or make_pyunite_window(state, buf)


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
