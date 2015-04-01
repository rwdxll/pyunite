import vim
import random
import wrapt
from functools import wraps
from funcy import autocurry


functions = {}


def vim_cast(value):
    if value is None:
        return ''
    elif isinstance(value, bool):
        return str(int(value))
    elif isinstance(value, str):
        return '"' + value + '"'
    elif isinstance(value, tuple):
        return str(list(value))
    else:
        return str(value)


def export(scope='local'):
    def wrapper(wrapped):
        global functions

        code = wrapped.func_code
        name = wrapped.func_name
        args_names = code.co_varnames[:code.co_argcount]
        args_string = ', '.join(args_names)
        functions[name] = wrapped

        if scope == 'local':
            vim_name = 's:' + name
        elif scope == 'global':
            vim_name = name[0].upper() + name[1:]
        else:
            raise Exception('Unrecognized scope option')

        code = []
        code.append('function! ' + vim_name + '(' + args_string + ')')
        code.append('python << EOF')
        code.append('from pyunite.decorators import functions, vim_cast')

        eval_arg_commands = map(lambda x: 'vim.eval("a:{}")'.format(x), args_names)
        retvalue_string = 'vim_cast(functions["' + name + '"](' + ', '.join(eval_arg_commands) + '))'

        code.append('vim.command("return " + ' + retvalue_string + ')')
        code.append('EOF')
        code.append('endfunction')
        vim.command('\n'.join(code))

        return wrapped
    return wrapper
