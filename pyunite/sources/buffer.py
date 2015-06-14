import vim
import re

from ..core import command_output, icompact
from ..actions import directory_actions
from ..variables import candidate


def get_candidates(*args):
    # Example of a candidate
    # 15 %a   "pyunite/sources/buffer.py"    line 10
    lines = icompact(command_output('ls').split('\n'))
    to_candidate = lambda x: candidate._replace(pre=x[0], filterable=x[1])
    return map(lambda x: to_candidate(re.split('"(.*)"', x)), lines)


actions = directory_actions
default_action = actions['window_open']


def actionable_string(action, candidate):
    return candidate.filterable


def syntaxes():
    return [
        'syntax match {source}_name /[^/ \[\]]\+\s/ contained',
        'syntax match {source}_prefix /\d\+\s\%(\S\+\)\?/ contained',
        'syntax match {source}_info /\[.\{{-}}\] / contained',
        'syntax match {source}_modified /\[.\{{-}}+\]/ contained',
        'syntax match {source}_nofile /\[nofile\]/ contained',
        'syntax match {source}_time /(.\{{-}}) / contained',
    ]


def highlights():
    return [
        'highlight default link {source}_name Function',
        'highlight default link {source}_prefix Constant',
        'highlight default link {source}_info PreProc',
        'highlight default link {source}_modified Statement',
        'highlight default link {source}_nofile Function',
        'highlight default link {source}_time Statement',
    ]
