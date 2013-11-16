from util import classproperty
from . import Defaults
from event import ActivityEvent, DecisionEvent, SignalEvent
from activity import ActivityCompleted

class Workflow(object):
    """ 
    Business logic that ties activities together. Core lies in decide() which commands
    the execution flow of a workflow task. It returns either an activity to execute
    or signals the task to be completed or terminated.
    """
    activities = []
    timeout = Defaults.WORKFLOW_TIMEOUT

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

    def respond_to_completed_activity(self, process, activity, result):
        raise NotImplementedError()

    def respond_to_interrupted_activity(self, process, activity, result):
        raise NotImplementedError()

    def respond_to_signal(self, process, signal):
        raise NotImplementedError()

    def decide(self, process):
        decisions = []

        def ensure_list(decision_or_list):
            if not decision_or_list:
                return []
            elif type(decision_or_list) == list:
                return decision_or_list
            else:
                return [decision_or_list]

        def uniquify(lst):
            unique = []
            for x in lst:
                if not x in unique:
                    unique.append(x)
            return unique

        if len(process.history) == 0:
            return ensure_list(self.initiate(process))

        for event in process.unseen_events():
            if isinstance(event, ActivityEvent):
                if isinstance(event.result, ActivityCompleted):
                    decisions += ensure_list(self.respond_to_completed_activity(process, event.activity, event.result))
                else:
                    decisions += ensure_list(self.respond_to_interrupted_activity(process, event.activity, event.result))
            elif isinstance(event, SignalEvent):
                decisions += ensure_list(self.respond_to_signal(process, event.signal))

        return uniquify(decisions)