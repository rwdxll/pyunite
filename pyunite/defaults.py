import vim
import funcy as fn


# Options and their default values
# 
# Notice that 'bufhidden' is set to 'wipe' by default. This means that all
# PyUnite buffers are guaranteed to be displayed in at least one window.
options = dict(
    # Scope of PyUnite's state. Possible values are:
    #
    #   global          One PyUnite buffer maintained globally. The quickfix
    #                   list behaves like this.
    #   tabpage         One PyUnite buffer maintained per tab.
    #   window          One PyUnite buffer maintained per window.
    #
    # Notice that there could actually be more than one PyUnite buffer
    # per scope if other PyUnite buffers in the same scope are marked as
    # 'reusable'.
    scope = 'tab',
    # Should focus be switched from current window to PyUnite window?
    focus_on_open = True,
    # When another PyUnite buffer is being opened in the same scope, should
    # this buffer be reused?
    reusable = True,
    # Should the PyUnite window be closed after performing an action on a
    # candidate?
    quit_after_action = False,
    # Height if horizontal split. Width if vertical split. Zero means don't
    # resize the window.
    size = 0,
    # Type of split and direction. This will let us know how the PyUnite
    # window was opened.
    vsplit = False,
    direction = 'leftabove',
)

# This state dictionary contains all the information ever needed to render a
# PyUnite window. States are buffer-local to PyUnite buffers.
state = fn.merge(options, dict(
    # Random string uniquely identifying a PyUnite's buffer.
    #
    # Whenever a PyUnite buffer is created, a variable in the PyBuffer
    # container's namespace (g:, t: or w:) is set which is equal to this
    # field. That way we can pair a PyUnite's buffer with its container.
    uid = '',
    sources = {},
))

source = dict(
    name = '',
    args = [],
    candidates = [],
)
