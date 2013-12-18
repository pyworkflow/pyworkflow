class ActivityExecution(object):
    def __init__(self, activity, id, input=None):
        self.activity = activity
        self.id = id
        self.input = input

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'ActivityExecution(%s, %s, %s)' % (self.activity, self.id, self.input)

class ActivityResult(object):
    def __init__(self, result_type):
        self.type = result_type
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __str__(self):
        return repr(self)

class InterruptedActivityResult(ActivityResult, Exception):
    def __init__(self, result_type):
        super(InterruptedActivityResult, self).__init__(result_type)

class ActivityCompleted(ActivityResult):
    def __init__(self, result=None):
        super(ActivityCompleted, self).__init__('completed')
        self.result = result

    def __repr__(self):
        return 'ActivityCompleted(%s)' % self.result

class ActivityCanceled(InterruptedActivityResult):
    ''' The cancelation of an activity '''
    def __init__(self, details=None):
        super(ActivityCanceled, self).__init__('canceled')
        self.details = details

    def __repr__(self):
        return 'ActivityCanceled(%s)' % self.details

class ActivityFailed(InterruptedActivityResult):
    ''' The failure of an activity '''
    def __init__(self, reason=None, details=None):
        super(ActivityFailed, self).__init__('failed')
        self.reason = reason
        self.details = details

    def __repr__(self):
        return 'ActivityFailed(%s,%s)' % (self.reason, self.details)

class ActivityTimedOut(InterruptedActivityResult):
    ''' The time out of an activity '''
    def __init__(self, details=None):
        super(ActivityTimedOut, self).__init__('timedout')
        self.details = details

    def __repr__(self):
        return 'ActivityTimedOut(%s)' % self.details