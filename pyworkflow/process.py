from uuid import uuid4
from events import DecisionEvent, ActivityEvent, ProcessStartedEvent
from activity import ActivityExecution
from decision import ScheduleActivity
from itertools import ifilter

class Process(object):
    def __init__(self, workflow=None, id=None, input=None, tags=None, history=None, parent=None):
        try:
            self._workflow = workflow.name
        except:
            self._workflow = str(workflow)

        self._id = id
        self._parent = parent
        self._input = input
        self._history = history or [ProcessStartedEvent()]
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

    def copy_with_id(self, id, **kwargs):
        return Process(workflow=self.workflow, id=id, input=self.input, tags=self.tags, parent=self.parent, **kwargs)

    def unseen_events(self):
        r_history = list(reversed(self.history))
        first_decision = next(ifilter(lambda ev: ev.type == 'decision', r_history), None)
        last_seen_idx = r_history.index(first_decision) if first_decision else len(r_history)
        return r_history[:last_seen_idx]

    def unfinished_activities(self):
        execution_for_decision = lambda decision: ActivityExecution(decision.activity, decision.id, decision.input)
        is_completed_activity = lambda ev: ev.type == 'activity' and hasattr(ev, 'result')
        is_scheduled_activity = lambda ev: ev.type == 'decision' and hasattr(ev.decision, 'activity')

        r_history = list(reversed(self.history)) # consume iterator once, store in list
        finished = [ev.activity_execution for ev in r_history if is_completed_activity(ev)]
        scheduled = [execution_for_decision(ev.decision) for ev in r_history if is_scheduled_activity(ev)]
        return filter(lambda ae: ae not in finished, scheduled)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __str__(self):
        return repr(self)

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
    def __init__(self, reason=None, details=None):
        super(ProcessCanceled, self).__init__('canceled')
        self.reason = reason
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