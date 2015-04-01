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


# ideas ----------------
#
# directory with:
#   doc.txt
#   <source_name>.py
#       - get_candidates()
#       - actions dictionary. (provide default dictionaries for common groups
#       of actions)
#       - default action
#       - description
#
# to allow custom arguments... maybe have some preprocessor logic going on at
# the command line? For example if we want to define a mapping for output:
#
#  nnoremap <leader>o PyUniteStart output:ls<CR>
#
# But then we would have to define a new mapping for every command. Another
# option is how Unite does it: it has custom code that prompts the user for
# the input depending on the source. <--- Uggghhh!!
# How about we get awesome and allow preprocessing directives a la shell
#   
#   nnoremap <leader>o PyUniteStart output:${ command? }
#
# Then PyUnite will automatically prompt the user and the user's input will
# become an argument for the source. All the other arguments will get parsed
# too, so in the following case:
#
#   nnoremap <leader>o PyUniteStart output:{%Vim Command: %}:other_opt
#   >> Vim Command: ls
#
# The args would be ['ls', 'other_opt']. Voila... flexible arguments I'm
# calling it.


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
def complete_cmdline(arglead, cmdline, cursorpos):
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
    options = fn.flatten(imap(formatted_option, variables.default_options.keys()))
    return filter(lambda x: arglead in x, options + sources.__all__)


def remove_state(state):
    if state['buffer'].valid:
        delete_buffer(state['buffer'])
    variables.states.remove(state)


@export()
def on_window_enter():
    # vim.windows haven't been updated yet on 'WinLeave'
    map(remove_state, ifilter(fn.complement(is_valid_state), variables.states))


@export()
def on_vim_leave_pre():
    with restore(vim.current.window), restore(vim.current.tabpage):
        grouped = fn.group_by(lambda x: x['tabpage_from'], variables.states)
        for tabpage, states in grouped.items():
            change_tabpage(tabpage)
            map(remove_state, states)


########################################################
# Data
########################################################


def escape_quote(string):
    return "'" + re.sub("'", "''", string) + "'"


def escape(char, string):
    return re.sub(char, '\\' + char, string)


def uniq(fun, lst):
    return imap(fn.first, fn.group_by(fun, lst).values())


def find(fun, lst):
    return next(ifilter(fun, lst), None)


def flatmap(fun, lst):
    '''
    map(fun, lst) should return a list of lists. Then flatten that
    '''
    return fn.iflatten(imap(fun, lst))


def icompact(lst):
    return ifilter(lambda x: x, lst)


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
        escape(' ', buffer_name),
    ))
    return vim.current.window


def change_window(window, autocmd=False):
    vim.command('silent {} {}wincmd w'.format('' if autocmd else 'noautocmd', window.number))


def resize_window(size, vsplit=False):
    vim.command('silent {} resize {}'.format('vertical' if vsplit else '', size))


def quit_window(autocmd=False):
    vim.command('silent {} close!'.format('' if autocmd else 'noautocmd'))


def make_buffer(name, autocmd=False):
    vim.command('silent {} edit {}'.format('' if autocmd else 'noautocmd', escape(' ', name)))
    return vim.current.buffer


def change_buffer(buff, autocmd=False):
    vim.command('silent {} {}buffer'.format('' if autocmd else 'noautocmd', buff.number))


def delete_buffer(buff, autocmd=False):
    vim.command('silent {} bdelete! {}'.format('' if autocmd else 'noautocmd', buff.number))


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
    return dict(imap(parse_option, options))


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
    fmt = lambda x: '{} {} {} {}'.format(source['name'], x.pre, x.filterable, x.post)
    return imap(fmt, source['candidates'])


def formatted_option(option):
    if isinstance(variables.default_options[option], bool):
        return ['-' + re.sub('_', '-', option), '-no-' + re.sub('_', '-', option)]
    else:
        return ['-' + re.sub('_', '-', option) + '=']


########################################################
# Core
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


def command_output(command):
    vim.command('redir => __command__output__ | silent! ' + command + ' | redir END')
    output = vim.eval('__command__output__')
    vim.command('unlet __command__output__')
    return output


def window_with_buffer(buff, windows=None):
    windows = windows if windows else vim.windows
    return find(lambda w: w.buffer == buff, windows)


def is_valid_state(state):
    # When a tabpage/window/buffer is closed, its 'valid' attribute becomes
    # False.  The 'vim' module does not have a 'valid' attribute, but then
    # again, any state with global scope is valid unless its underlying buffer
    # has been closed.
    return state['buffer'].valid and getattr(state['container'], 'valid', True)


def candidates_len(state):
    return sum(imap(lambda x: len(x['candidates']), state['sources']))


def filterables(source):
    '''
    A filterable is the part of a candidate that can be filtered
    '''
    return imap(lambda x: x.filterable, source['candidates'])


def same_sources(s1, s2):
    return (fn.pluck('name', s1['sources']) == fn.pluck('name', s2['sources']) and
            fn.pluck('args', s1['sources']) == fn.pluck('args', s2['sources']))


def vhas(option):
    return bool(int(vim.eval('has("' + option + '")')))


def vexists(option):
    return bool(int(vim.eval('exists("' + option + '")')))


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
        buff.append(list(contents), 0)


def set_buffer_syntax(state):
    vim.command('syntax clear')
    for source in state['sources']:
        source_module(source).set_syntax()
    vim.command('syntax sync minlines=1 maxlines=1')


def make_buffer_name(state):
    return '{}{} pyunite:{} ({})'.format(
        '' if state['replace'] else '[NR] ',
        state['scope'][:3].upper(),
        str(uniqueid())[:7],
        candidates_len(state),
    )


def make_pyunite_buffer(state, autocmd=False):
    with restore(vim.current.buffer):
        buff = make_buffer(make_buffer_name(state))
    set_buffer_options(buff)
    set_buffer_autocommands(buff)
    set_buffer_mappings(buff)
    set_buffer_contents(buff, flatmap(formatted_candidates, state['sources']))
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
        vsplit = state['vsplit'],
        size = state['size'],
        buffer_name = state['buffer'].name,
        autocmd = autocmd,
    )
    set_window_options(window)
    return window


def populate_candidates(state):
    for source in state['sources']:
        source['candidates'] = source_module(source).get_candidates(*source['args'])


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
    old_window = window_with_buffer(old_state['buffer']) if old_state else None

    if not old_state or not old_window:
        window = make_pyunite_window(state, autocmd=True)

    elif (state['vsplit'], state['direction']) == (old_state['vsplit'], old_state['direction']):
        change_window(old_window, autocmd=True)
        resize_window(state['size'] or old_state['size'], vsplit=state['vsplit'])
        window = old_window

    else:
        change_window(old_window)
        with restore(vim.current.window), scoped(state['buffer'].options, bufhidden='hide'):
            quit_window()
        window = make_pyunite_window(state, autocmd=True)

    state['size'] = window.width if state['vsplit'] else window.height
    return window


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
        because it will be needed later on to compare it with the current
        state and determine whether the window should be resized/moved, etc...
    '''
    # We are only interested in buffers which are in the same container.
    # That's where the interesting reuse/replace logic is at.
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
        set_buffer_contents(state['buffer'], flatmap(formatted_candidates, state['sources']))
        variables.states.remove(replaceable)
        echo('Replaced buffer {}'.format(state['buffer']))
        return replaceable

    with_same_sources = find(partial(same_sources, state), states)
    if with_same_sources:
        state['sources'] = with_same_sources['sources']
    else:
        populate_candidates(state)
    state['buffer'] = make_pyunite_buffer(state)
    echo('Created buffer {}'.format(state['buffer']))


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
    }[state['scope']]
    old_state = buffer_logic(state)
    if state['close_on_empty'] and candidates_len(state) == 0:
        return
    saved = vim.current.window
    window = window_logic(state, old_state)
    set_buffer_syntax(state)
    if not state['focus_on_open']:
        change_window(saved, autocmd=True)
    variables.states.append(state)
