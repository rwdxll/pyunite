import funcy as fn
import itertools 
import operator


# Not really curried but yeah!
silent = fn.silent
first = fn.first
_not = fn.complement
compose = fn.compose
iden = fn.identity
iflatten = fn.iflatten
curry = fn.curry

# lambda magic is necessary since funcy uses the '__code__' attribute of the
# function being curried but built-ins don't have it.
# I know currying built-ins sacrifices performance but this is not a real-time
# system. Simplicity FTW!
equal = fn.autocurry(lambda x,y: x==y)
nequal = fn.autocurry(lambda x,y: x!=y)
imap = fn.autocurry(lambda x,y: itertools.imap(x,y))
ifilter = fn.autocurry(lambda x,y: itertools.ifilter(x,y))
concat = fn.autocurry(lambda x,y: operator.concat(x,y))
startswith = fn.autocurry(lambda x,y: y.startswith(x))
map_ = fn.autocurry(lambda x,y: map(x,y))
filter_ = fn.autocurry(lambda x,y: filter(x,y))

# funcy's own functions curried!
pluck = fn.autocurry(fn.pluck)
where = fn.autocurry(fn.where)
merge = fn.autocurry(fn.merge)
groupby = fn.autocurry(fn.group_by)
