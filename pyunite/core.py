import re
import vim
import funcy as fn
from importlib import import_module
from uuid import uuid4 as uniqueid
from itertools import ifilter, imap
from functools import partial
from operator import itemgetter, contains
from contextlib import contextmanager

from . import variables, sources
from .pure import *
from .exceptions import *
from .decorators import export


@export()
def start(cmdline):
    ''' Entry point '''
    with exception_to_vim_errormsg():
        start_unite(fn.merge(variables.state, parse_state(cmdline)))


@export()
def complete_cmdline(arglead, cmdline, cursorpos):
    ''' Look at help for :command-completion-customlist '''
    sources_and_options = list(fmt_options(variables.options.keys())) + sources.__all__
    return filter(lambda x: x.startswith(arglead), sources_and_options)


def remove_state(state):
    state['buffer'].valid and delete_buffer(state['buffer'])
    variables.states.remove(state)


@export()
def win_enter():
    ''' Remove invalid states
    We have to do this on WinEnter because vim.windows hasn't been updated yet
    on WinLeave
    '''
    map(remove_state, ifilter(invalid_state, variables.states))


@export()
def vim_leave_pre():
    ''' Remove all pyunite states in each tabpage '''
    with restore(vim.current.window), restore(vim.current.tabpage):
        states_by_tab = fn.group_by(itemgetter('tabpage_from'), variables.states)
        # error(str(dict(states_by_tab)))
        for tabpage, states in states_by_tab.items():
            change_tabpage(tabpage)
            map(remove_state, states)


@contextmanager
def exception_to_vim_errormsg():
    try:
        yield
    except PyUniteWarning as e:
        warn(str(e), store=True)
    except PyUniteError as e:
        error(str(e), store=True)
    except AssertionError as e:
        # It's better to provide a stack trace than nothing
        if not str(e):
            raise
        warn(str(e))


@contextmanager
def scoped(dictobj, **mappings):
    ''' Change values in a dictionary for the duration of this context. Then
    restore the old values '''
    saved = {key : dictobj[key] for key in mappings.keys()}
    for key, val in mappings.items():
        dictobj[key] = val
    try:
        yield
    finally:
        for key, val in saved.items():
            dictobj[key] = val


@contextmanager
def restore(vimobj, autocmd=False):
    ''' Restore a vim object (tabpage, window, etc...) after inversion of
    control is done '''
    saved = vimobj
    change_func = {
        type(vim.current.tabpage): change_tabpage,
        type(vim.current.window): change_window,
        type(vim.current.buffer): change_buffer,
    }[type(vimobj)]
    try:
        yield
    finally:
        if saved.valid:
            change_func(saved, autocmd)


@contextmanager
def highlight(higroup):
    ''' Set highlight group for the duration of this context '''
    vim.command('echohl ' + higroup)
    try:
        yield
    finally:
        vim.command('echohl None')


def echo(msg, high='Normal', store=False):
    with highlight(high):
        if high == 'ErrorMsg':
            echo_cmd = 'echoe'
        elif store:
            echo_cmd = 'echon'
        else:
            echo_cmd = 'echom'
        vim.command(echo_cmd + "'" + escape_quote(msg) + "'")


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


def resize_window(size, vsplit=False, autocmd=False):
    vim.command('silent {} {} resize {}'.format(
        '' if autocmd else 'noautocmd',
        'vertical' if vsplit else '',
        size
    ))


def quit_window(autocmd=False):
    vim.command('silent {} close!'.format('' if autocmd else 'noautocmd'))


def make_buffer(name, autocmd=False):
    vim.command('silent {} edit {}'.format('' if autocmd else 'noautocmd', escape(' ', name)))
    return vim.current.buffer


def change_buffer(buff, autocmd=False):
    vim.command('silent {} {}buffer'.format('' if autocmd else 'noautocmd', buff.number))


def delete_buffer(buff, autocmd=False):
    vim.command('silent {} bdelete! {}'.format('' if autocmd else 'noautocmd', buff.number))


def vhas(option):
    return bool(int(vim.eval('has("' + option + '")')))


def vexists(option):
    return bool(int(vim.eval('exists("' + option + '")')))


def source_module(source):
    return import_module('pyunite.sources.' + source['name'])


def command_output(command):
    vim.command('redir => __command__output__ | silent! ' + command + ' | redir END')
    output = vim.eval('__command__output__')
    vim.command('unlet __command__output__')
    return output


def window_with_buffer(buff, windows=None):
    return find(lambda w: w.buffer == buff, windows or vim.windows)


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
        vim.command('autocmd {} <buffer={}> call s:{}()'.format(
            event,
            buff.number,
            handler.func_name,
        ))
    vim.command('augroup END')


def set_buffer_options(buff):
    buff.options['bufhidden'] = 'wipe'
    buff.options['buflisted'] = False
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


def get_included_syntax_name(syntaxes):
    ''' Sometimes the user would like to include a syntax file in a syntax
    command (:h syn-include). '''
    def get_it(syntax_cmd):
        return fn.first(re.findall('include (@\w+) ', syntax_cmd))
    return fn.first(fn.keep(imap(get_it, syntaxes)))


def set_buffer_syntax(state):
    vim.command('syntax clear')
    for source in state['sources']:
        module = source_module(source)
        included_syntax = get_included_syntax_name(module.syntaxes())
        what_makes_the_magic_happen = [
            'syntax match {source}_source_name /^{source}/ contained',
            'syntax region {source} oneline keepend start=/^{source}/ end=/$/ contains=' + (included_syntax or '') + ',{source}_.*',
            'highlight default link {source}_source_name Comment',
        ]
        map(
            lambda cmd: vim.command(cmd.format(source=source['name'])),
            module.syntaxes() + module.highlights() + what_makes_the_magic_happen
        )
    vim.command('syntax sync minlines=1 maxlines=1')


def make_buffer_name(state):
    return '{}{} pyunite:{} ({})'.format(
        '' if state['replace'] else '[NR] ',
        state['scope'][:3].upper(),
        str(uniqueid())[:7],
        len(list(aggregate_candidates(state))),
    )


def make_pyunite_buffer(state, autocmd=False):
    with restore(vim.current.buffer):
        buff = make_buffer(make_buffer_name(state))
    buff.vars['pyunite_uid'] = state['uid']
    set_buffer_options(buff)
    set_buffer_autocommands(buff)
    set_buffer_mappings(buff)
    set_buffer_contents(buff, aggregate_candidates(state))
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


def populated_candidates(state):
    for source in state['sources']:
        source['candidates'] = source_module(source).get_candidates(*source['args'])
    return state['sources']


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
        # If bufhidden=wipe, buffer will dissapear when we close its window
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

    with_same_sources = partial(same_sources, state)

    reusable_state = fn.first(fn.where(
        ifilter(with_same_sources, states),
        replace = state['replace']
    ))

    replaceable_state = fn.first(fn.where(
        ifilter(lambda x: not with_same_sources(x), states),
        replace = True
    ))

    old_state = None

    if reusable_state:
        state.update(fn.project(reusable_state, ['uid', 'buffer', 'sources']))
        old_state = reusable_state
        variables.states.remove(reusable_state)

    elif replaceable_state:
        state.update(fn.project(replaceable_state, ['uid', 'buffer']))
        state['sources'] = populated_candidates(state)
        set_buffer_contents(state['buffer'], aggregate_candidates(state))
        old_state = replaceable_state
        variables.states.remove(replaceable_state)

    else:
        same = find(with_same_sources, states)
        state['sources'] = (same and same['sources']) or populated_candidates(state)
        state['buffer'] = make_pyunite_buffer(state)

    return old_state


def start_unite(state):
    validate_state(state)
    state['uid'] = str(uniqueid())
    state['tabpage_from'] = vim.current.tabpage
    state['window_from'] = vim.current.window
    state['container'] = {
        'global': vim,
        'tabpage': vim.current.tabpage,
        'window': vim.current.window
    }[state['scope']]
    old_state = buffer_logic(state)
    if state['close_on_empty'] and len(list(aggregate_candidates(state))) == 0:
        return
    saved = vim.current.window
    window_logic(state, old_state)
    set_buffer_syntax(state)
    if not state['focus_on_open']:
        change_window(saved, autocmd=True)
    variables.states.append(state)
