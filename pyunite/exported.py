import vim
from vim_bridge import bridged

from .helpers import parse_cmdline


@bridged
def PyUniteStart(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteResume(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteClose(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteFromCurrentDir(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteFromBufferDir(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteFromProjectDir(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteFromCustomDir(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteFromCursorWord(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteFromInitialInput(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteFirst(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteLast(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteNext(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUnitePrevious(cmdline):
    start_unite(*parse_cmdline(cmdline))


@bridged
def PyUniteCompleteBuffer(arglead, cmdline, cursorpos):
    '''
    Provide a list of completion candidates for PyUnite* commands

    Args:
        arglead (str):    The leading portion of the argument currently being completed on
        cmdline (str):    The entire command line
        cursorpos (int):  The cursor position in it (byte index)

    Returns:
        list: List of completion candidates

    Notes:
        For more information, refer to the help for :command-completion-customlist
    '''
    pass


@bridged
def PyUniteCompleteSource(arglead, cmdline, cursorpos):
    '''
    Provide a list of completion candidates for PyUnite* commands

    Args:
        arglead (str):    The leading portion of the argument currently being completed on
        cmdline (str):    The entire command line
        cursorpos (int):  The cursor position in it (byte index)

    Returns:
        list: List of completion candidates

    Notes:
        For more information, refer to the help for :command-completion-customlist
    '''
    pass


def start_unite(args, options):
    pass
