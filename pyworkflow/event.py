from datetime import datetime

class Event(object):
    def __init__(self, event_type, **kwargs):
        self.type = event_type
        self.datetime = kwargs.get('datetime', datetime.now())
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

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