import re
import funcy as fn
from itertools import imap, ifilter
from functools import partial

from . import variables
from . import sources
from .exceptions import *


# a -> a
def iden(x):
    return x

# str -> str
def escape_quote(string):
    return re.sub("'", "''", string)


# str -> str
def escape(char, string):
    return re.sub(char, '\\' + char, string)


# hashable b => (a -> b) -> [a] -> [a]
def iuniq(func, lst):
    return imap(fn.first, fn.group_by(func, lst).itervalues())


# (a -> bool) -> [a] -> a
def find(func, lst):
    return fn.first(ifilter(func, lst))


# (a -> b) -> [[a]] -> [b]
def iflatmap(func, lst):
    return fn.iflatten(imap(func, lst))


# [a] -> [a]
def icompact(lst):
    return ifilter(iden, lst)


# str -> state
def parse_state(string):
    spaces_with_no_backslashes = r'((?<!\\)\s)+'
    tokens = filter(lambda x: x!=' ', re.split(spaces_with_no_backslashes, string))
    options = map(parse_option, (ifilter(lambda x: x.startswith('-'), tokens)))
    sources = map(parse_source, (ifilter(lambda x: x and not x.startswith('-'), tokens)))
    map(validate_option, options)
    map(validate_source, sources)
    return fn.merge(dict(options), dict(sources=sources))


# str -> source
def parse_source(string):
    colons_with_no_backslashes = r'(?<!\\):'
    splits = re.split(colons_with_no_backslashes, string)
    return fn.merge(variables.source, dict(name=splits[0], args=splits[1:]))


# source -> None
def validate_source(source):
    assert source['name'] in sources.__all__, 'Source "{}" is not recognized'.format(source['name'])
    return source


# str -> option
def parse_option(string):
    if '=' not in string:
        string += '='
    name, value = re.split('=', string)
    if value == '':
        value = False if name.startswith('-no-') else True
    else:
        value = fn.silent(eval)(value) or value
    name = re.sub('-', '_', re.sub('^(-no-|-)', '', name))
    return variables.option._replace(name=name, value=value)


# option -> None
def validate_option(option):
    original_name = '-' + re.sub('_', '-', option.name)
    error_msg = 'Option "{}" is not recognized'.format(original_name)
    assert option.name in variables.options, error_msg
    expected_type = type(variables.options[option.name])
    error_msg = 'Expected value of {} for option "{}"'.format(str(expected_type), original_name)
    assert type(option.value) == expected_type, error_msg


# state -> None
def validate_state(state):
    assert len(state['sources']), 'You need to specify a source name'
    scopes = ['global', 'tabpage', 'window']
    assert state['scope'] in scopes, 'Option "-scope" has to be one of {}'.format(str(scopes))
    directions = ['topleft', 'botright', 'leftabove', 'rightbelow']
    assert state['direction'] in directions, 'Option "-direction" has to be one of {}'.format(str(directions))


# state -> [candidates]
def aggregate_candidates(state):
    return fn.iflatten(imap(lambda x: fmt_candidates(x['name'], x['candidates']), state['sources']))


# str -> [candidate] -> [candidate]
def fmt_candidates(source_name, candidates):
    return imap(partial(fmt_candidate, source_name), candidates)


# str -> candidate -> candidate
def fmt_candidate(source_name, candidate):
    return '{} {} {} {}'.format(source_name, candidate.pre, candidate.filterable, candidate.post)


# [option] -> [option]
def fmt_options(options):
    return fn.iflatten(imap(fmt_option, options))


# option -> option
def fmt_option(option):
    if isinstance(variables.options[option], bool):
        return ['-' + re.sub('_', '-', option), '-no-' + re.sub('_', '-', option)]
    else:
        return ['-' + re.sub('_', '-', option) + '=']


# state -> bool
def invalid_state(state):
    # When a tabpage/window/buffer is closed, its 'valid' attribute becomes
    # False.  The 'vim' module does not have a 'valid' attribute, but then
    # again, any state with global scope is valid unless its underlying buffer
    # has been closed.
    return not state['buffer'].valid or not getattr(state['container'], 'valid', True)


# state -> state -> bool
def same_sources(s1, s2):
    ''' Do two states have the same sources (same names and same arguments)?  '''
    return (
        fn.pluck('name', s1['sources']) == fn.pluck('name', s2['sources']) and
        fn.pluck('args', s1['sources']) == fn.pluck('args', s2['sources'])
    )
