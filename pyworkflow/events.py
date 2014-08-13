from datetime import datetime
from copy import deepcopy

class Event(object):
    def __init__(self, event_type, **kwargs):
        self.type = event_type
        self.datetime = kwargs.get('datetime', datetime.now())
        
    def __eq__(self, other):
        other = deepcopy(other)
        other.datetime = self.datetime
        return self.__dict__ == other.__dict__

class DecisionStartedEvent(Event):
    def __init__(self, **kwargs):
        super(DecisionStartedEvent, self).__init__('decision_started', **kwargs)
        
    def __repr__(self):
        return 'DecisionStartedEvent()'

class DecisionEvent(Event):
    def __init__(self, decision, **kwargs):
        super(DecisionEvent, self).__init__('decision', **kwargs)
        self.decision = decision

    def __repr__(self):
        return 'DecisionEvent(%s)' % (repr(self.decision))

class ActivityStartedEvent(Event):
    def __init__(self, activity_execution, **kwargs):
        super(ActivityStartedEvent, self).__init__('activity_started', **kwargs)
        self.activity_execution = activity_execution

    def __repr__(self):
        return 'ActivityStartedEvent(%s)' % (self.activity_execution)

class ActivityEvent(Event):
    def __init__(self, activity_execution, result, **kwargs):
        super(ActivityEvent, self).__init__('activity', **kwargs)
        self.activity_execution = activity_execution
        self.result = result

    def __repr__(self):
        return 'ActivityEvent(%s, %s)' % (self.activity_execution, repr(self.result))

class SignalEvent(Event):
    def __init__(self, signal, **kwargs):
        super(SignalEvent, self).__init__('signal', **kwargs)
        self.signal = signal

    def __repr__(self):
        return 'SignalEvent(%s)' % (repr(self.signal))

class TimerEvent(Event):
    def __init__(self, timer, **kwargs):
        super(TimerEvent, self).__init__('timer', **kwargs)
        self.timer = timer

    def __repr__(self):
        return 'TimerEvent(%s)' % (repr(self.timer))

class ProcessStartedEvent(Event):
    def __init__(self, **kwargs):
        super(ProcessStartedEvent, self).__init__('process_started', **kwargs)
        
    def __repr__(self):
        return 'ProcessStartedEvent()'

class ChildProcessEvent(Event):
    def __init__(self, process_id, result, **kwargs):
        super(ChildProcessEvent, self).__init__('child_process', **kwargs)
        self.process_id = process_id
        self.result = result

        self.tags = kwargs.get('tags', None)
        self.workflow = kwargs.get('workflow', None)

    def __repr__(self):
        return 'ChildProcessEvent(%s, %s, tags=%s, workflow=%s)' % (repr(self.process_id), repr(self.result), repr(self.tags), repr(self.workflow))