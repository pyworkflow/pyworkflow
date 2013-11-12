from datetime import datetime
#from decision import ScheduleActivity, CompleteWorkflow, TerminateWorkflow
'''
class Event(object):
    class Type(object):
        ACTIVITY_SCHEDULED = Type('ACTIVITY_SCHEDULED')
        ACTIVITY_COMPLETED = Type('ACTIVITY_COMPLETED')
        ACTIVITY_ABORTED = Type('ACTIVITY_ABORTED')
        ACTIVITY_FAILED = Type('ACTIVITY_FAILED')
        WORKFLOW_COMPLETED = Type('WORKFLOW_COMPLETED')
        WORKFLOW_TERMINATED = Type('WORKFLOW_TERMINATED')

        def __init__(self, name):
            self.name = name

    def __init__(self, event_type, **kwargs):
        self.type = event_type
        self.datetime = kwargs.get('datetime', datetime.now())

    @classmethod
    def from_decision(cls, decision):
        if isinstance(decision, ScheduleActivity):
            return Event(Event.Type.ACTIVITY_SCHEDULED, activity=decision.activity, input=decision.input)
        elif isinstance(decision, CompleteWorkflow):
            return Event(Event.Type.WORKFLOW_COMPLETED, result=decision.result)
        elif isinstance(decision, TerminateWorkflow):
            return Event(Event.Type.WORKFLOW_TERMINATED, reason=decision.reason)
'''


class Event(object):
    def __init__(self, **kwargs):
        self.datetime = kwargs.get('datetime', datetime.now())

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class DecisionEvent(Event):
    def __init__(self, decision, **kwargs):
        super(DecisionEvent, self).__init__(**kwargs)

        self.decision = decision

    def __repr__(self):
        return '[DecisionEvent: %s]' % self.decision

class ActivityEvent(Event):
    def __init__(self, activity, result, **kwargs):
        super(ActivityEvent, self).__init__(**kwargs)
        
        self.activity = activity
        self.result = result

    def __repr__(self):
        return '[ActivityEvent: %s, %s]' % (self.activity, self.result)