import re
import vim
import funcy as fn
from importlib import import_module as module
from contextlib import contextmanager
from functools import partial
from itertools import ifilter
from pathlib import Path

from . import defaults, sources
from .exceptions import UnrecognizedOption, UnrecognizedSource


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
    return fn.merge(options, {'sources': sources})


def parse_sources(strings):
    return map(parse_source, strings) 


def parse_source(string):
    colons_with_no_backslashes = r'(?<!\\):'
    splits = re.split(colons_with_no_backslashes, string)
    return fn.merge(defaults.source, dict(
        name = validate_source(splits[0]),
        args = splits[1:],
    ))


def validate_source(name):
    if name not in sources.__all__:
        raise UnrecognizedSource(name)
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
    if name not in defaults.options:
        raise UnrecognizedOption(name)
    if type(value) != type(defaults.options[name]):
        raise TypeError('Expected {} for {}'.format(type(defaults.options[name]), name))
    return name, value


def source_module(source):
    return module('pyunite.sources.' + source['name'])


def command_output(command):
    vim.command('redir => __command__output__ | silent! ' + command + ' | redir END')
    output = vim.eval('__command__output__')
    vim.command('unlet __command__output__')
    return output


@contextmanager
def scoped(dictobj, **mappings):
    '''
    Replace mappings in 'dictobj' with 'mappings' and restore them afterwards
    '''
    saved = { key : dictobj[key] for key in mappings.keys() }
    for key, val in mappings.items():
        dictobj[key] = val
    try:
        yield
    finally:
        for key, val in saved.items():
            dictobj[key] = val


def windo_and_back(function, windows=vim.windows):
    saved = vim.current.window
    try:
        for window in windows:
            change_window(window)
            function(window)
    finally:
        change_window(saved)


def bufdo_and_back(function, buffers=vim.buffers):
    saved = vim.current.buffer
    try:
        for buffer in buffers:
            change_buffer(buffer)
            function(buffer)
    finally:
        change_buffer(saved)


@contextmanager
def highlight(higroup):
    vim.command('echohl ' + higroup)
    try:
        yield
    finally:
        vim.command('echohl None')


def escape_quote(string):
    return "'" + re.sub("'", "''", string) + "'"


def echo(msg, high='Normal', store=False):
    with highlight(high):
        vim.command(('echon ' if store else 'echom ') + escape_quote(msg))


warn = partial(echo, high='WarningMsg')
error = partial(echo, high='ErrorMsg')


def vhas(option):
    return bool(int(vim.eval('has("' + option + '")')))


def vexists(option):
    return bool(int(vim.eval('exists("' + option + '")')))


def uniq(fun, lst):
    return map(fn.first, fn.group_by(fun, lst).values())


def find(fun, lst):
    return next(ifilter(fun, lst), None)


def window_with_number(number, windows=vim.windows):
    return find(lambda w: w.number == number, windows)


def window_with_buffer(buffer, windows=vim.windows):
    return find(lambda w: w.buffer == buffer, windows)


def buffer_with_number(number, buffers=vim.buffers):
    return find(lambda b: b.number == number, buffers)


def buffer_with_name(name, buffers=vim.buffers):
    # We need to do this because Python's buffer object's name property is
    # given as an absolute path.
    return find(lambda b: b.name == Path(name).absolute().as_posix(), buffers)


def is_pyunite_buffer(buffer):
    return buffer.options['filetype'] == 'pyunite'


def is_windows():
    return sys.platform == 'win32'


def is_cygwin():
    return sys.platform == 'cygwin'


def is_mac():
    return sys.platform == 'darwin'


def is_unix():
    return vhas('unix')


def is_cmdwin():
    return vim.current.buffer.name == '[Command Line]'


def get_cmdline():
    return vim.eval('histget(":")')


########################################################
# UI
########################################################

def make_window(buffer=None):
    vim.command('silent noautocmd new ' + ('' if buffer is None else buffer.name))


def change_window(window):
    vim.command('silent noautocmd ' + str(window.number) + 'wincmd w')


def close_window(window):
    change_window(window)
    vim.command('silent noautocmd wincmd q')
    vim.command('silent noautocmd wincmd w')


def change_buffer(buffer):
    vim.command('silent noautocmd ' + str(buffer.number) + 'buffer')


def edit_buffer(name):
    vim.command('silent noautocmd edit ' + name)


def make_buffer(name):
    saved = vim.current.buffer
    edit_buffer(name)
    change_buffer(saved)
    return buffer_with_name(name)
