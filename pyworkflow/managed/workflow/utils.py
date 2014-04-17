import itertools

def ensure_iter(obj):
    return obj if hasattr(obj, '__iter__') else [obj]

def flatten(list_of_lists):
    return itertools.chain(*list_of_lists)

def unique(col):
    return reduce(lambda acc, x: acc+[x] if not x in acc else acc, col, [])
