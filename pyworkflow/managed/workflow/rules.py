class RuleDoesNotApplyException(Exception):
    pass

class Rule(object):
    def __init__(self, match, handler):
        self._match = match
        self._handler = handler

    def match(self, ev):
        return self._match(ev)

    def __call__(self, instance, event, process):
        if not self.match(event):
            raise RuleDoesNotApplyException()
        return self._handler(instance, event, process)

    def __repr__(self):
        return 'Rule (%s)' % (repr(self._handler))


# DECORATORS

def match_exact_or_filter(value, match_val):
    """ returns whether value matches match_val, either directly or by applying as filter fn """
    if not match_val:
        return True

    if hasattr(match_val, '__call__'):
        # is function, treat as filter
        try:
            return match_val(value)
        except:
            return False
    else:
        # no function, do direct comparison
        return value == match_val

def rule(match):
    """Decorator that creates a Rule out of the decorated function"""
    def decorator(handler_fn):
        return Rule(match, handler_fn)
    return decorator

def process_started(*args):
        
    match = lambda ev: ev.type == 'process_started'
    
    if len(args) and hasattr(args[0], '__call__'):
        # called without params, fn supplied as arg
        return Rule(match, args[0])
    else:
        # called with params, need to return decorator
        return rule(match)

def completed_activity(activity=None, input=None):
    def match(ev):
        # match event type first
        m = ev.type == 'activity' and ev.result.type == 'completed'
        m = m and match_exact_or_filter(ev.activity_execution.activity, activity)
        m = m and match_exact_or_filter(ev.activity_execution.input, input)
        return m
    return rule(match)

def interrupted_activity(activity=None, result=None):
    def match(ev):
        # match event type first
        m = ev.type == 'activity' and ev.result.type != 'completed'
        m = m and match_exact_or_filter(ev.activity_execution.activity, activity)
        m = m and match_exact_or_filter(ev.result, result)
        return m
    return rule(match)

def signal(name=None):
    def match(ev):
        # match event type
        m = ev.type == 'signal'
        m = m and match_exact_or_filter(ev.signal.name, name)
        return m
    return rule(match)

def timer(data=None):
    def match(ev):
        # match event type
        m = ev.type == 'timer'
        m = m and match_exact_or_filter(ev.timer.data, data)
        return m
    return rule(match)

def child_process_completed(workflow=None, tags=None, has_tag=None, result=None):
    def match(ev):
        # match event type
        m = ev.type == 'child_process'
        m = m and match_exact_or_filter(ev.workflow, workflow)
        m = m and match_exact_or_filter(ev.tags, tags)
        m = m and match_exact_or_filter(ev.result, result)
        m = m and (not has_tag or has_tag in ev.tags)
        return m
    return rule(match)