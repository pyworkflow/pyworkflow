from uuid import uuid4
from .activity import Activity

class Decision(object):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class CompleteProcess(Decision):
    def __init__(self, result=None):
        self.result = result

    def __repr__(self):
        return '[CompleteProcess: %s]' % (str(self.result))

class TerminateProcess(Decision):
    def __repr__(self):
        return '[TerminateProcess]'

class ScheduleActivity(Decision):
    def __init__(self, activity, id=None, category=None, input=None):
        if isinstance(activity, Activity):
            self.activity = activity.__class__.name
        elif type(activity) is type:
            self.activity = activity.name
        else:
            self.activity = str(activity)
            
        self.id = id or str(uuid4())
        self.category = category
        self.input = input

    def __repr__(self):
        return '[ScheduleActivity: %s(%s)]' % (self.activity, self.input)