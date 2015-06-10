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
autocurry = fn.autocurry
subdict = fn.project

# lambda magic is necessary since funcy uses the '__code__' attribute of the
# function being curried but built-ins don't have it.
# I know currying built-ins sacrifices performance but this is not a real-time
# system. Simplicity FTW!
equal = autocurry(lambda x,y: x==y)
nequal = autocurry(lambda x,y: x!=y)
imap = autocurry(lambda x,y: itertools.imap(x,y))
ifilter = autocurry(lambda x,y: itertools.ifilter(x,y))
concat = autocurry(lambda x,y: operator.concat(x,y))
startswith = autocurry(lambda x,y: y.startswith(x))
map_ = autocurry(lambda x,y: map(x,y))
filter_ = autocurry(lambda x,y: filter(x,y))

# funcy's own functions curried!
pluck = autocurry(fn.pluck)
where = autocurry(fn.where)
merge = autocurry(fn.merge)
groupby = autocurry(fn.group_by)
