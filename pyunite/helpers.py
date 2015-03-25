import re
import funcy as fn

from .exceptions import UnrecognizedOption


# It was unite#helper#parse_options_args() before
def parse_cmdline(cmd_str):
    # Split by spaces except spaces preceded by backslash
    tokens = [ x for x in re.split('((?<!\\\)\s)+', cmd_str) if x != ' ' ]
    options = parse_options([ x for x in tokens if x and x.startswith('-') ])
    map(lambda (x,y): validate_option(x, y), options.items())
    sources = parse_sources([ x for x in tokens if x and not x.startswith('-') ])
    return sources, options


def validate_option(name, value):
    if name not in default_context and not name.startswith('custom_'):
        raise UnrecognizedOption(name)
    if type(value) != type(default_context[name]):
        raise TypeError('Expected {} for {}'.format(type(default_context[name]), name))


def parse_sources(sources):
    # return: dict of <source_name> -> [<source_argument>]
    return { x[0] : x[1:] for x in map(parse_source, sources) }


def parse_source(source):
    # Split by colons except colons preceded by backslash
    return re.split('(?<!\\\):', source)


def parse_options(options):
    # return: dict of <option_name> -> <option_value>
    options = [ x + ('' if '=' in x else '=') for x in options ]
    return { name : value for name, value in map(parse_option, options) }
    

def parse_option(option):
    name, value = re.split('=', option)
    if value == '':
        value = False if name.startswith('-no-') else True
    else:
        value = fn.silent(eval)(value) or value
    name = re.sub('-', '_', re.sub('^(-no-|-)', '', name))
    return name, value
