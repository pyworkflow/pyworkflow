from rules import RuleDoesNotApplyException
from utils import unique, flatten, ensure_iter
from base import Workflow


class RuleSetMetaclass(type):
    def __init__(cls, name, bases, attrs):
        super(RuleSetMetaclass, cls).__init__(name, bases, attrs)
        cls._initialize_rules(name, bases, attrs)

    def _initialize_rules(cls, name, bases, attrs):
        is_rule = lambda p: hasattr(p, 'match')
        cls.ruleset = [a for a in attrs.values() if is_rule(a)]


class RuleSetWorkflow(Workflow):
    __metaclass__ = RuleSetMetaclass

    def handle_event(self, event, process):
        def decisions_from_rule(rule):
            try:
                decisions = rule(self, event, process)
                if decisions:
                    return ensure_iter(decisions)
                else:
                    return None
            except RuleDoesNotApplyException:
                return None

        decisions = [decisions_from_rule(rule) for rule in self.ruleset]
        decisions = filter(lambda d: d is not None, decisions) # ignore null-decisions
        return flatten(decisions)

    def decide(self, process):
        handler = lambda ev: filter(bool, self.handle_event(ev, process))
        decisions = map(handler, process.unseen_events()) # list of lists of decisions
        return unique(flatten(decisions))