import itertools
from ..util import classproperty
from ..defaults import Defaults
from ..events import ActivityEvent, DecisionEvent, SignalEvent
from ..activity import ActivityCompleted

class Workflow(object):
    """ 
    Business logic that ties activities together. Core lies in decide() which commands
    the execution flow of a workflow task. It returns either an activity to execute
    or signals the task to be completed or terminated.
    """
    activities = []
    timeout = Defaults.WORKFLOW_TIMEOUT
    decision_timeout = Defaults.DECISION_TIMEOUT

    @classproperty
    def name(cls):
        name = cls.__name__
        if name.endswith('Workflow') and len(name) > 8:
            return name[:-8]
        return name
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def decide(self, process):
        ''' Take the next decision for the process in this workflow '''
        raise NotImplementedError()

class DefaultWorkflow(Workflow):
    def initiate(self, process):
        raise NotImplementedError()

    def respond_to_completed_activity(self, process, activity_execution, result):
        raise NotImplementedError()

    def respond_to_interrupted_activity(self, process, activity_execution, details):
        raise NotImplementedError()

    def respond_to_signal(self, process, signal):
        raise NotImplementedError()

    def handle_event(self, event, process):
        if isinstance(event, ActivityEvent):
            if isinstance(event.result, ActivityCompleted):
                return self.respond_to_completed_activity(process, event.activity_execution, event.result.result)
            else:
                return self.respond_to_interrupted_activity(process, event.activity_execution, event.result.details)
        elif isinstance(event, SignalEvent):
            return self.respond_to_signal(process, event.signal)

    def decide(self, process):
        ensure_iter = lambda x: x if hasattr(x, '__iter__') else [x]

        if len(process.history):
            handler = lambda ev: filter(bool, ensure_iter(self.handle_event(ev, process)))
            decisions = itertools.chain(*itertools.imap(handler, process.unseen_events()))
            return reduce(lambda acc, d: acc+[d] if not d in acc else acc, decisions, [])
        else:
            return ensure_iter(self.initiate(process))