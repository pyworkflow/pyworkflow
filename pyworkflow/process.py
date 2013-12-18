from uuid import uuid4
from events import DecisionEvent, ActivityEvent
from activity import ActivityExecution
from decision import ScheduleActivity

class Process(object):
    def __init__(self, workflow=None, id=None, input=None, tags=None, history=None, parent=None):
        try:
            self._workflow = workflow.name
        except:
            self._workflow = str(workflow)

        self._id = id
        self._parent = parent
        self._input = input
        self._history = history or []
        self._tags = tags or []
        
    @property
    def workflow(self):
        return self._workflow

    @property
    def id(self):
        return self._id

    @property
    def parent(self):
        return self._parent

    @property
    def input(self):
        return self._input

    @property
    def history(self):
        return self._history
    
    @property
    def tags(self):
        return self._tags

    def copy_with_id(self, id):
        return Process(workflow=self.workflow, id=id, input=self.input, tags=self.tags, parent=self.parent)

    def unseen_events(self):
        def before_decision(iterable):
            event = next(iterable, None)
            return [] if not event or hasattr(event, 'decision') else [event] + before_decision(iterable)

        return before_decision(reversed(self.history))

    def unfinished_activities(self):
        def unfinished(iterable):
            event = next(iterable, None)
            if event is None:
                return []
            elif event.type == 'decision' and hasattr(event.decision, 'activity'):
                return unfinished(iterable) + [ActivityExecution(event.decision.activity, event.decision.id, event.decision.input)]
            elif event.type == 'activity' and hasattr(event, 'result'):
                return filter(lambda x: x != event.activity_execution, unfinished(iterable))
            else:
                return unfinished(iterable)

        return unfinished(reversed(self.history))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return 'Process(%s, %s, %s, %s, %s)' % (self.workflow, self.id, self.input, self.tags, self.parent)



class ProcessResult(object):
    def __init__(self, result_type):
        self.type = result_type
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class InterruptedProcessResult(ProcessResult, Exception):
    def __init__(self, result_type):
        super(InterruptedProcessResult, self).__init__(result_type)

class ProcessCompleted(ProcessResult):
    def __init__(self, result=None):
        super(ProcessCompleted, self).__init__('completed')
        self.result = result

    def __repr__(self):
        return 'ProcessCompleted(%s)' % self.result

class ProcessCanceled(InterruptedProcessResult):
    ''' The cancelation of a process '''
    def __init__(self, details=None):
        super(ProcessCanceled, self).__init__('canceled')
        self.details = details

    def __repr__(self):
        return 'ProcessCanceled(%s)' % self.details

class ProcessFailed(InterruptedProcessResult):
    ''' The failure of a process '''
    def __init__(self, reason=None, details=None):
        super(ProcessFailed, self).__init__('failed')
        self.reason = reason
        self.details = details

    def __repr__(self):
        return 'ProcessFailed(%s,%s)' % (self.reason, self.details)

class ProcessTimedOut(InterruptedProcessResult):
    ''' The time out of a process '''
    def __init__(self, details=None):
        super(ProcessTimedOut, self).__init__('timedout')
        self.details = details

    def __repr__(self):
        return 'ProcessTimedOut(%s)' % self.details