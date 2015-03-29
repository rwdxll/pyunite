import re
import vim
import funcy as fn
from pathlib import Path
from copy import deepcopy
from functools import partial
from hashlib import sha256
from importlib import import_module as module
from itertools import ifilter, imap
from uuid import uuid4 as uniqueid
from operator import itemgetter as get
from contextlib import contextmanager, nested

from . import variables, sources
from .decorators import export


class PyUniteException(Exception):
    pass


@export()
def start(cmdline):
    start_unite(fn.merge(variables.default_state, parse_cmdline(cmdline)))


@export()
def resume(cmdline):
    start_unite(fn.merge(variables.default_state, parse_cmdline(cmdline)))


@export()
def close(cmdline):
    start_unite(fn.merge(variables.default_state, parse_cmdline(cmdline)))


@contextmanager
def scoped(dictobj, **mappings):
    '''Replace mappings in 'dictobj' with 'mappings' and restore them afterwards'''
    saved = {opt : dictobj[opt] for opt in mappings.keys()}
    map(lambda opt, val: setter(dictobj, opt, val), items())
    try:
        yield
    finally:
        map(lambda opt, val: setter(dictobj, opt, val), saved.items())


@contextmanager
def preserve_current_tabpage(autocmd=False):
    saved = vim.current.tabpage
    try:
        yield
    finally:
        if saved.valid:
            change_window(saved, autocmd)


@contextmanager
def preserve_current_window(autocmd=False):
    saved = vim.current.window
    try:
        yield
    finally:
        if saved.valid:
            change_window(saved, autocmd)


@contextmanager
def preserve_current_buffer(autocmd=False):
    saved = vim.current.buffer
    try:
        yield
    finally:
        if saved.valid:
            change_buffer(saved, autocmd)


def source_module(source):
    return module('pyunite.sources.' + source['name'])


def command_output(command):
    vim.command('redir => __command__output__ | silent! ' + command + ' | redir END')
    output = vim.eval('__command__output__')
    vim.command('unlet __command__output__')
    return output


def vhas(option):
    return bool(int(vim.eval('has("' + option + '")')))


def vexists(option):
    return bool(int(vim.eval('exists("' + option + '")')))


########################################################
# Data
########################################################


def escape_quote(string):
    return "'" + re.sub("'", "''", string) + "'"


def uniq(fun, lst):
    return map(fn.first, fn.group_by(fun, lst).values())


def find(fun, lst):
    return next(ifilter(fun, lst), None)


########################################################
# UI
########################################################


@contextmanager
def highlight(higroup):
    vim.command('echohl ' + higroup)
    try:
        yield
    finally:
        vim.command('echohl None')


def echo(msg, high='Normal', store=False):
    with highlight(high):
        vim.command(('echon ' if store else 'echom ') + escape_quote(msg))


warn = partial(echo, high='WarningMsg')
error = partial(echo, high='ErrorMsg')


def change_tabpage(tabpage, autocmd=False):
    vim.command('silent {} tabnext {}'.format('' if autocmd else 'noautocmd', tabpage.number))


def make_window(direction='', vsplit=False, size=0, buffer_name='', autocmd=False):
    vim.command('silent {} {} {}{} {}'.format(
        '' if autocmd else 'noautocmd',
        direction,
        str(size) if size > 0 else '',
        'vnew' if vsplit else 'new',
        buffer_name,
    ))
    return vim.current.window


def change_window(window, autocmd=False):
    vim.command('silent {} {}wincmd w'.format('' if autocmd else 'noautocmd', window.number))


def quit_window(autocmd=False):
    vim.command('silent {} close!'.format('' if autocmd else 'noautocmd'))


def make_buffer(name, autocmd=False):
    vim.command('silent {} edit {}'.format('' if autocmd else 'noautocmd', name))
    return vim.current.buffer


def change_buffer(buffer, autocmd=False):
    vim.command('silent {} {}buffer'.format('' if autocmd else 'noautocmd', buffer.number))


########################################################
# Parsers/Formatters
########################################################


def parse_cmdline(cmdline):
    '''
    Parse the string after ':<command>' into a state dictionary

    Args:
        cmdline (str): The string after ':<command>'

    Returns:
        dict: Parsed state from command line
    '''
    spaces_with_no_backslashes = r'((?<!\\)\s)+'
    tokens = [ x for x in re.split(spaces_with_no_backslashes, cmdline) ]
    options = parse_options([ x for x in tokens if x and x != ' ' and x.startswith('-') ])
    sources = parse_sources([ x for x in tokens if x and x != ' ' and not x.startswith('-') ])
    if not sources:
        raise PyUniteException('You need to specify at least one source')
    return fn.merge(options, {'sources': sources})


def parse_sources(strings):
    return map(parse_source, strings) 


def parse_source(string):
    colons_with_no_backslashes = r'(?<!\\):'
    splits = re.split(colons_with_no_backslashes, string)
    return fn.merge(variables.default_source, dict(
        name = validate_source(splits[0]),
        args = splits[1:],
    ))


def validate_source(name):
    if name not in sources.__all__:
        raise PyUniteException('Unrecognized source: ' + name)
    return name


def parse_options(strings):
    options = [ x + ('' if '=' in x else '=') for x in strings ]
    return { name : value for name, value in map(parse_option, options) }
    

def parse_option(string):
    name, value = re.split('=', string)
    if value == '':
        value = False if name.startswith('-no-') else True
    else:
        value = fn.silent(eval)(value) or value
    name = re.sub('-', '_', re.sub('^(-no-|-)', '', name))
    return validate_option(name, value)


def validate_option(name, value):
    if name not in variables.default_options:
        raise PyUniteException('Unrecognized option: ' + name)
    if type(value) != type(variables.default_options[name]):
        raise TypeError('Expected {} for {}'.format(type(variables.default_options[name]), name))
    return name, value


def formatted_candidates(source):
    return imap(lambda x: source['name'] + '  ' + x, source['candidates'])


def formatted_source_name(source):
    return source['name'] + '(' + str(len(source['candidates'])) + ')'


def formatted_source_names(sources):
    return imap(formatted_source_name, sources)


def formatted_option(option):
    if isinstance(variables.default_options[option], bool):
        return ['-' + re.sub('_', '-', option), '-no-' + re.sub('_', '-', option)]
    else:
        return ['-' + re.sub('_', '-', option) + '=']


def state_is_invalid(state):
    # When a tabpage/window/buffer is closed, its 'valid' field becomes False
    return hasattr(state['container'], 'valid') and not state['container'].valid


@export()
def on_window_enter():
    # If a window was closed, vim.windows will have been updated by now, but
    # not when 'WinLeave' happens.
    quit_pyunite_states(ifilter(state_is_invalid, variables.states))

    # Close PyUnite window if it's last in tab
    if len(vim.windows) == 1 and vim.current.buffer.options['filetype'] == 'pyunite':
        state = find(lambda x: x['buffer'] == vim.current.buffer, variables.states)
        quit_pyunite_state(state)


@export()
def on_vim_leave_pre():
    quit_pyunite_states(variables.states)


def set_buffer_options(buff):
    buff.options['bufhidden'] = 'wipe'
    buff.options['buflisted'] = True
    buff.options['buftype'] = 'nofile'
    buff.options['completefunc'] = ''
    buff.options['omnifunc'] = ''
    buff.options['iskeyword'] += ',-,+,\\,!,~'
    buff.options['matchpairs'] = re.sub('<:>,', '', buff.options['matchpairs'])
    buff.options['modeline'] = False
    buff.options['modifiable'] = False
    buff.options['readonly'] = False
    buff.options['swapfile'] = False
    buff.options['filetype'] = 'pyunite'


handlers = dict(
    # InsertEnter   = export()(on_insert_enter),
    # InsertLeave   = export()(on_insert_leave),
    # CursorHoldI   = export()(on_cursor_hold_i),
    # CursorMovedI  = export()(on_cursor_moved_i),
    # CursorMoved   = export()(on_cursor_moved),
    # CursorMovedI  = export()(on_cursor_moved),
    # BufHidden     = export()(on_buf_unload),
    # BufUnload     = export()(on_buf_unload),
    # BufWinEnter   = export()(on_bufwin_enter),
    # InsertCharPre = export()(on_insert_char_pre),
    # TextChanged   = export()(on_text_changed),
)


def set_buffer_autocommands(buff):
    vim.command('augroup plugin-pyunite')
    vim.command('autocmd! * <buffer={}>'.format(buff.number))
    for event, handler in handlers:
        vim.command('autocmd {} <buffer={}> call s:{}({})'.format(event, buff.number, handler.func_name))
    vim.command('augroup END')


def set_buffer_mappings(buff):
    pass


def set_buffer_contents(state, buff):
    with scoped(buff.options, modifiable=True):
        buff[:] = None
        content = fn.flatten(imap(formatted_candidates, state['sources']))
        buff.append(content, 0)


def make_pyunite_buffer(state):
    with preserve_current_buffer():
        buff = make_buffer('pyunite:{}'.format(str(uniqueid())[:7]))
    set_buffer_options(buff)
    set_buffer_autocommands(buff)
    set_buffer_mappings(buff)
    set_buffer_contents(state, buff)
    return buff


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


def make_pyunite_window(state, autocmd=False):
    with preserve_current_window():
        window = make_window(
            autocmd,
            direction = state['direction'],
            size = state['size'],
            vsplit = state['vsplit'],
            buffer_name = state['buffer'].name,
        )
    set_window_options(window)
    return window


def sources_names(state):
    return map(get('name'), state['sources'])


def quit_pyunite_states(states):
    with preserve_current_window(), preserve_current_tabpage():
        map(quit_pyunite_state, states)


def quit_pyunite_state(state):
    # Closing the window will wipeout the buffer
    change_tabpage(state['tabpage'])
    change_window(state['window'])
    quit_window(state['window'])
    variables.states.remove(state)


def total_candidates(state):
    return sum(imap(lambda x: len(x['candidates']), state['sources']))


def siblings(state):
    return filter(lambda x: x['container'] == state['container'], variables.states)


def validate_state(state):
    assert state['scope'] in ['global', 'tab', 'window']
    assert state['direction'] in ['topleft', 'botright', 'leftabove', 'rightbelow']


def start_unite(state):
    validate_state(state)
    state['tabpage'] = vim.current.tabpage
    state['window'] = vim.current.window
    state['container'] = {
        'global': vim,
        'tabpage': vim.current.tabpage,
        'window': vim.current.window
    }[state.pop('scope')]
    states = siblings(state)

    equivalent = find(lambda x: sources_names(x) == sources_names(state), states)
    if equivalent:
        if state['focus_on_open']:
            change_window(equivalent['window'])
        return

    quittable = find(get('quittable'), states)
    if quittable:
        with preserve_current_window():
            quit_pyunite_state(quittable)

    for source in state['sources']:
        source['candidates'] = source_module(source).gather_candidates()
    if total_candidates(state) == 0 and state['close_on_empty']:
        return

    state['buffer'] = make_pyunite_buffer(state)

    # Trigger autocmds
    saved = vim.current.window
    make_pyunite_window(state, autocmd=True)
    if not state['focus_on_open']:
        change_window(saved, autocmd=True)


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
    formatted = fn.flatten(imap(formatted_option, variables.default_options.keys()))
    return filter(lambda x: arglead in x, formatted)
