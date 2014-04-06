from uuid import uuid4

class Decision(object):
    def __init__(self, decision_type):
        self.type = decision_type

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class CompleteProcess(Decision):
    def __init__(self, result=None):
        super(CompleteProcess, self).__init__('complete_process')

        self.result = result

    def __repr__(self):
        return 'CompleteProcess(%s)' % (str(self.result))

class CancelProcess(Decision):
    def __init__(self, details=None, reason=None):
        super(CancelProcess, self).__init__('cancel_process')

        self.details = details
        self.reason = reason

    def __repr__(self):
        return 'CancelProcess(%s)' % (self.details)

class StartChildProcess(Decision):
    def __init__(self, process, child_policy='ABANDON'):
        super(StartChildProcess, self).__init__('start_child_process')

        self.process = process
        self.child_policy = child_policy

    def __repr__(self):
        return 'StartChildProcess(%s, %s)' % (self.process, self.child_policy)

class ScheduleActivity(Decision):
    def __init__(self, activity, id=None, category=None, input=None):
        super(ScheduleActivity, self).__init__('schedule_activity')
        
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
        super(CancelActivity, self).__init__('cancel_activity')
        
        self.id = activity_or_id.id if hasattr(activity_or_id, 'id') else activity_or_id

    def __repr__(self):
        return 'CancelActivity(%s)' % self.id

class Timer(Decision):
    def __init__(self, delay, data=None):
        super(Timer, self).__init__('timer')
        self.delay = delay
        self.data = data or {}

    def __repr__(self):
        return 'Timer(%s, %s)' % (self.delay, self.data)