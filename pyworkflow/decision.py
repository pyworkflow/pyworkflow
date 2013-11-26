from uuid import uuid4
from .activity import Activity
from copy import copy

class Decision(object):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class CompleteProcess(Decision):
    def __init__(self, result=None):
        self.result = result

    def __repr__(self):
        return 'CompleteProcess(%s)' % (str(self.result))

class CancelProcess(Decision):
    def __init__(self, details=None, reason=None):
        self.details = details
        self.reason = reason

    def __repr__(self):
        return 'CancelProcess(%s)' % (self.details)

class ScheduleActivity(Decision):
    def __init__(self, activity, id=None, category=None, input=None):
        try:
            self.activity = activity.name
        except:
            self.activity = str(activity)
            
        self.id = id or str(uuid4())
        self.category = category
        self.input = input

    def __repr__(self):
        return 'ScheduleActivity(%s, %s)' % (self.activity, self.input)

class CancelActivity(Decision):
    def __init__(self, activity_or_id):
        self.id = activity_or_id.id if hasattr(activity_or_id, 'id') else activity_or_id

    def __repr__(self):
        return 'CancelActivity(%)' % self.id