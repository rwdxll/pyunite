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
from operator import itemgetter as get, not_
from contextlib import contextmanager, nested

from . import variables, sources
from .decorators import export


class PyUniteException(Exception):
    pass


########################################################
# Exported
########################################################


@export()
def start(cmdline):
    start_unite(fn.merge(variables.default_state, parse_cmdline(cmdline)))


@export()
def resume(cmdline):
    start_unite(fn.merge(variables.default_state, parse_cmdline(cmdline)))


@export()
def close(cmdline):
    start_unite(fn.merge(variables.default_state, parse_cmdline(cmdline)))


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


@export()
def on_window_enter():
    # If a window was closed, vim.windows will have been updated by now, but
    # not when 'WinLeave' happens.
    map(wipe_pyunite_state, ifilter(fn.complement(is_valid_state), variables.states))

    # Close PyUnite window if it's last in tab
    if len(vim.windows) == 1 and vim.current.buffer.options['filetype'] == 'pyunite':
        state = find(lambda x: x['buffer'] == vim.current.buffer, variables.states)
        wipe_pyunite_state(state)


@export()
def on_vim_leave_pre():
    with restore(vim.current.window), restore(vim.current.tabpage):
        for tabpage in vim.tabpages:
            change_tabpage(tabpage)
            for window in ifilter(lambda x: is_pyunite_buffer(x.buffer), vim.windows):
                change_window(window)
                state = state_with_buffer(window.buffer)
                if state['ephemeral']:
                    # Close all windows displaying the buffer
                    delete_buffer()
                    variables.states.remove(state)
                else:
                    # XXX: Save state (cache?)
                    pass


########################################################
# Generic
########################################################


@contextmanager
def scoped(dictobj, **mappings):
    saved = { key : dictobj[key] for key in mappings.keys() }
    for key, val in mappings.items():
        dictobj[key] = val
    try:
        yield
    finally:
        for key, val in saved.items():
            dictobj[key] = val


@contextmanager
def restore(vimobj, autocmd=False):
    saved = {
        type(vim.current.tabpage): vim.current.tabpage,
        type(vim.current.window): vim.current.window,
        type(vim.current.buffer): vim.current.buffer,
    }[type(vimobj)]
    try:
        yield
    finally:
        if saved.valid:
            change_func = {
                type(vim.current.tabpage): change_tabpage,
                type(vim.current.window): change_window,
                type(vim.current.buffer): change_buffer,
            }[type(vimobj)]
            change_func(saved, autocmd)


def source_module(source):
    return module('pyunite.sources.' + source['name'])


def is_pyunite_buffer(buff):
    return buff.options['filetype'] == 'pyunite'


def command_output(command):
    vim.command('redir => __command__output__ | silent! ' + command + ' | redir END')
    output = vim.eval('__command__output__')
    vim.command('unlet __command__output__')
    return output


def window_with_buffer(buff, windows=None):
    windows = windows if windows else vim.windows
    return find(lambda w: w.buffer == buff, windows)


def state_with_buffer(buff, states=None):
    states = states if states else variables.states
    return find(lambda x: x['buffer'] == buff, states)


def is_valid_state(state):
    # When a tabpage/window/buffer is closed, its 'valid' attribute becomes
    # False.  The 'vim' module does not have a 'valid' attribute, but then
    # again, any state with global scope is valid unless its underlying buffer
    # has been closed.
    return state['buffer'].valid and getattr(state['container'], 'valid', True)


def total_candidates(state):
    return sum(imap(lambda x: len(x['candidates']), state['sources']))


def all_candidates(state):
    return fn.iflatten(imap(formatted_candidates, state['sources']))


def same_sources(s1, s2):
    return (fn.pluck('name', s1['sources']) == fn.pluck('name', s2['sources']) and
            fn.pluck('args', s1['sources']) == fn.pluck('args', s2['sources']))


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


def resize_window(size, vsplit=False):
    vim.command('silent {} resize {}'.format('vertical' if vsplit else '', size))


def quit_window(autocmd=False):
    vim.command('silent {} close!'.format('' if autocmd else 'noautocmd'))


def make_buffer(name, autocmd=False):
    vim.command('silent {} edit {}'.format('' if autocmd else 'noautocmd', name))
    return vim.current.buffer


def change_buffer(buff, autocmd=False):
    vim.command('silent {} {}buffer'.format('' if autocmd else 'noautocmd', buff.number))


def delete_buffer(autocmd=False):
    vim.command('silent {} bdelete!'.format('' if autocmd else 'noautocmd'))


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


########################################################
# Core
########################################################


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


def set_buffer_mappings(buff):
    pass


def set_buffer_contents(buff, contents):
    with scoped(buff.options, modifiable=True):
        buff[:] = None
        buff.append(contents, 0)


def make_pyunite_buffer(state, autocmd=False):
    with restore(vim.current.buffer):
        buff = make_buffer('{}pyunite:{}'.format(
            '' if state['replace'] else '[no-repl]:',
            str(uniqueid())[:7],
        ))
    set_buffer_options(buff)
    set_buffer_autocommands(buff)
    set_buffer_mappings(buff)
    set_buffer_contents(buff, list(all_candidates(state)))
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
    window = make_window(
        direction = state['direction'],
        size = state['size'],
        vsplit = state['vsplit'],
        buffer_name = state['buffer'].name,
        autocmd = autocmd,
    )
    set_window_options(window)
    return window


def populate_candidates(state):
    for source in state['sources']:
        source['candidates'] = source_module(source).gather_candidates()


def buffer_logic(state):
    '''
    Buffer create/replace/reuse logic. The function name is not very good :(

       new_state    |   old_state   | same sources |     action
    ----------------|---------------|--------------|-----------------
        replace     |    replace    |    True      |  reuse buffer
        replace     |    replace    |    False     |  replace buffer
        replace     |   no-replace  |    True      |  create buffer (copy candidates)
        replace     |   no-replace  |    False     |  create buffer
       no-replace   |    replace    |    True      |  create buffer (copy candidates)
       no-replace   |    replace    |    False     |  create buffer
       no-replace   |   no-replace  |    True      |  reuse buffer
       no-replace   |   no-replace  |    False     |  create buffer

    A reusable buffer will be looked for, then a replacement buffer and as a
    last resort a new one will be created.

    Returns:
        old_state (dict): In case a state was reused/replaced it is returned
        because it will be needed later on to determine wheter the PyUnite
        window should be resized/moved, etc...
    '''
    states = fn.where(variables.states, container=state['container'])

    is_reusable = lambda x: x['replace'] == state['replace'] and same_sources(x, state)
    reusable = find(is_reusable, states)
    if reusable:
        state['buffer'] = reusable['buffer']
        state['sources'] = reusable['sources']
        variables.states.remove(reusable)
        echo('Reused buffer {}'.format(state['buffer']))
        return reusable

    is_replaceable = lambda x: x['replace'] == state['replace'] == True and not same_sources(x, state)
    replaceable = find(is_replaceable, states)
    if replaceable:
        state['buffer'] = replaceable['buffer']
        populate_candidates(state)
        set_buffer_contents(state['buffer'], list(all_candidates(state)))
        variables.states.remove(replaceable)
        echo('Replaced buffer {}'.format(state['buffer']))
        return replaceable

    with_same_sources = find(partial(same_sources, state), states)
    if with_same_sources:
        state['sources'] = with_same_sources['sources']

    populate_candidates(state)
    state['buffer'] = make_pyunite_buffer(state)
    echo('Created buffer {}'.format(state['buffer']))


def window_logic(state, old_state):
    '''
    Window create/resize logic. The function name is not very good :(

      new_state  |   old_state   | same directions | same size |  action
    -------------|---------------|-----------------|-----------|-----------
      vertical   |    vertical   |      True       |   True    |  reuse
      vertical   |    vertical   |      True       |   False   |  resize
      vertical   |    vertical   |      False      |   True    |  close old; create
      vertical   |    vertical   |      False      |   False   |  close old; create
      vertical   |   horizontal  |      True       |   True    |  close old; create
      vertical   |   horizontal  |      True       |   False   |  close old; create
      vertical   |   horizontal  |      False      |   True    |  close old; create
      vertical   |   horizontal  |      False      |   False   |  close old; create
     horizontal  |    vertical   |      True       |   True    |  close old; create
     horizontal  |    vertical   |      True       |   False   |  close old; create
     horizontal  |    vertical   |      False      |   True    |  close old; create
     horizontal  |    vertical   |      False      |   False   |  close old; create
     horizontal  |   horizontal  |      True       |   True    |  reuse
     horizontal  |   horizontal  |      True       |   False   |  resize
     horizontal  |   horizontal  |      False      |   True    |  close old; create
     horizontal  |   horizontal  |      False      |   False   |  close old; create
    '''
    if not old_state or not window_with_buffer(old_state['buffer']):
        return make_pyunite_window(state, autocmd=True)

    old_window = window_with_buffer(old_state['buffer'])

    if (state['vsplit'] == old_state['vsplit'] and 
            state['direction'] == old_state['direction']):
        change_window(old_window, autocmd=True)
        resize_window(state['size'], vsplit=state['vsplit'])
        return old_window

    with restore(vim.current.window), scoped(state['buffer'].options, bufhidden='hide'):
        change_window(old_window)
        quit_window()
    return make_pyunite_window(state, autocmd=True)


def validate_state(state):
    assert state['scope'] in ['global', 'tabpage', 'window']
    assert state['direction'] in ['topleft', 'botright', 'leftabove', 'rightbelow']


def start_unite(state):
    validate_state(state)
    state['tabpage_from'] = vim.current.tabpage
    state['window_from'] = vim.current.window
    state['container'] = {
        'global': vim,
        'tabpage': vim.current.tabpage,
        'window': vim.current.window
    }[state.pop('scope')]
    old_state = buffer_logic(state)
    if state['close_on_empty'] and total_candidates(state) == 0:
        return
    saved = vim.current.window
    window = window_logic(state, old_state)
    if not state['focus_on_open']:
        change_window(saved, autocmd=True)
    variables.states.append(state)
