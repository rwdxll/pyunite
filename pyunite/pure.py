import re
from functools import partial

from . import variables
from . import sources
from .curried import *
from .curried import _not


# str -> str
def escape_quote(string):
    return re.sub("'", "''", string)


# str -> str
def escape(char, string):
    return re.sub(char, '\\' + char, string)


# hashable b => (a -> b) -> [a] -> [a]
def iuniq(func, lst):
    return imap(first, groupby(func, lst).itervalues())


# (a -> bool) -> [a] -> a
def find(func, lst):
    return first(ifilter(func, lst))


# (a -> b) -> [[a]] -> [b]
def iflatmap(func, lst):
    return iflatten(imap(func, lst))


# [a] -> [a]
def icompact(lst):
    return ifilter(iden, lst)


# str -> state
def parse_state(string):
    spaces_with_no_backslashes = r'((?<!\\)\s)+'
    tokens = filter(nequal(' '), re.split(spaces_with_no_backslashes, string))
    options = map(parse_option, (ifilter(startswith('-'), tokens)))
    sources = map(parse_source, (ifilter(_not(startswith('-')), tokens)))
    map(validate_option, options)
    map(validate_source, sources)
    return merge(dict(options), dict(sources=sources))


# str -> source
def parse_source(string):
    colons_with_no_backslashes = r'(?<!\\):'
    splits = re.split(colons_with_no_backslashes, string)
    return merge(variables.source, dict(name=splits[0], args=splits[1:]))


# source -> None
def validate_source(source):
    assert source['name'] in sources.__all__
    return source


# str -> option
def parse_option(string):
    if '=' not in string:
        string += '='
    name, value = re.split('=', string)
    if value == '':
        value = False if name.startswith('-no-') else True
    else:
        value = silent(eval)(value) or value
    name = re.sub('-', '_', re.sub('^(-no-|-)', '', name))
    return variables.option._replace(name=name, value=value)


# option -> None
def validate_option(option):
    assert option.name in variables.options
    assert type(option.value) == type(variables.options[option.name])


# state -> None
def validate_state(state):
    assert len(state['sources'])
    assert state['scope'] in ['global', 'tabpage', 'window']
    assert state['direction'] in ['topleft', 'botright', 'leftabove', 'rightbelow']


# state -> [candidates]
def aggregate_candidates(state):
    return iflatten(imap(lambda x: fmt_candidates(x['name'], x['candidates']), state['sources']))


# str -> [candidate] -> [candidate]
def fmt_candidates(source_name, candidates):
    return imap(partial(fmt_candidate, source_name), candidates)


# str -> candidate -> candidate
def fmt_candidate(source_name, candidate):
    return '{} {} {} {}'.format(source_name, candidate.pre, candidate.filterable, candidate.post)


# [option] -> [option]
def fmt_options(options):
    return iflatten(imap(fmt_option, options))


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
same_sources = autocurry(lambda s1, s2: (
    pluck('name', s1['sources']) == pluck('name', s2['sources']) and
    pluck('args', s1['sources']) == pluck('args', s2['sources'])
))
