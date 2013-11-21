from datetime import datetime

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
        return 'DecisionEvent(%s)' % (repr(self.decision))

class ActivityEvent(Event):
    def __init__(self, activity, result, **kwargs):
        super(ActivityEvent, self).__init__(**kwargs)
        self.activity = activity
        self.result = result

    def __repr__(self):
        return 'ActivityEvent(%s, %s)' % (self.activity, repr(self.result))

class SignalEvent(Event):
    def __init__(self, signal, **kwargs):
        super(SignalEvent, self).__init__(**kwargs)
        self.signal = signal

    def __repr__(self):
        return 'SignalEvent(%s)' % (repr(self.signal))