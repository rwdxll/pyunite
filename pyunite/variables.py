import vim
import funcy as fn


# Notice that 'bufhidden' is set to 'wipe' by default. This means that all
# PyUnite buffers are guaranteed to be displayed in at least one window.

# Internal maintained list of currently active PyUnite states.
states = []

# Options can be specified in the PyUnite command line. They are merged into a
# state that uniquely identifies a PyUnite buffer.
default_options = dict(
    # *scope*
    #   Scope of a PyUnite buffer. Can be one of:
    #
    #       - global: One global PyUnite buffer. The quickfix list behaves like this.
    #       - tabpage: State is tab local.
    #       - window: State is window local. The location list behaves like this.
    #
    #   Notice that there could actually be more than one PyUnite buffer per scope
    #   if other PyUnite buffers in the same scope are marked as reusable.
    scope = 'tabpage',
    # Whether to quit if another PyUnite in the same scope is being opened
    quittable = True,
    # Don't open window when there are no candidates
    close_on_empty = False,
    # Steal focus from current window
    focus_on_open = False,
    # Close window after performing an action on a candidate
    close_on_action = False,
    # Leave window after performing an action on a candidate
    leave_on_action = False,
    # Height if horizontal split. Width if vertical split. Zero means don't
    # resize the window.
    size = 0,
    # Split vertically instead of horizontally
    vsplit = False,
    # Direction of the window split. See
    # https://technotales.wordpress.com/2010/04/29/vim-splits-a-guide-to-doing-exactly-what-you-want/ 
    direction = 'leftabove',
)

# This state dictionary contains all the information ever needed to render a
# PyUnite window. States are buffer-local to PyUnite buffers.
default_state = fn.merge(default_options, dict(
    sources = {},
    # Buffer to which this state belongs to
    buffer = None,
    # Window which was active at the time of command
    window = None,
    # Tab which was active at the time of command
    tabpage = None,
    # Depends on the value of 'scope':
    #   global => vim
    #   tab    => vim.current.tabpage
    #   window => vim.current.window
    container = None,
))

default_source = dict(
    name = '',
    args = [],
    candidates = [],
)
