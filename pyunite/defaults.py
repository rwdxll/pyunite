import vim
import funcy as fn


# Options and their default values
options = dict(
    # TODO: Redo this documentation
    # Scope of PyUnite's state. Possible values are:
    #
    #   global          Global. The quickfix list behaves like this.
    #   tabpage         PyUnite buffers in the same tab (as given by
    #   window          Local to window. The location list behaves like this.
    #
    # For example if the scope is 'tabpage', and a PyUnite window is opened,
    # it will create a state with tab scope (t:). This means that PyUnites in
    # other tabs will be unaffected.
    scope = 'tabpage',
    # Should the window be split vertically?
    vsplit = False,
    # Should focus be switched from current window to PyUnite window?
    focus_on_open = True,
    # Should the current window be used for rendering or should a new window
    # be created? Notice that in order to control the window layout you can
    # always use the usual suspects (:vert, :botright, :split, etc...)
    reuse_window = False,
    # Should the PyUnite window be closed after performing an action on a
    # candidate?
    quit_after_action = False,
)

# This state dictionary contains all the information ever needed to render a
# PyUnite window. States are buffer-local to PyUnite buffers.
state = fn.merge(options, dict(
    # ID identifying this state. No two states should ever have the same ID.
    # When a new PyUnite command is executed, an ID for the new state is
    # calculated and a PyUnite buffer with the same ID is reused if available.
    # The ID itself is calculated as a sha256 hash of the concatenation of
    # several fields:
    #   
    #   - This state's scope
    #   - 
    #
    state_id = '',
    # Well, height and width of the window. What else can I say? The one used
    # depends on various factors (is the new window a vertical/horizontal
    # split?, etc...)
    # The default value is taken from the quickfix window's default height.
    # A -1 means do not set the height, which will effectively split the
    # current buffer horizontally in half.
    height = 10,
    # A -1 means do not set the width, which will effectively split the
    # current buffer vertically in half
    width = -1,
    sources = {},
))

source = dict(
    name = '',
    args = [],
    candidates = [],
)
