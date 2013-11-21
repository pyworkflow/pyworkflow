class ActivityResult(object):
    def __init__(self):
        pass
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class InterruptedActivityResult(ActivityResult, Exception):
    def __init__(self):
        super(InterruptedActivityResult, self).__init__()

class ActivityCompleted(ActivityResult):
    def __init__(self, result=None):
        super(ActivityCompleted, self).__init__()
        self.result = result

    def __repr__(self):
        return 'ActivityCompleted(%s)' % self.result

class ActivityAborted(InterruptedActivityResult):
    ''' The abortion of an activity '''
    def __init__(self, details=None):
        super(ActivityAborted, self).__init__()
        self.details = details

    def __repr__(self):
        return 'ActivityAborted(%s)' % self.details

class ActivityFailed(InterruptedActivityResult):
    ''' The failure of an activity '''
    def __init__(self, reason=None, details=None):
        super(ActivityFailed, self).__init__()
        self.reason = reason
        self.details = details

    def __str__(self):
        return 'ActivityFailed(%s,%s)' % (self.reason, self.details)

class ActivityTimedOut(InterruptedActivityResult):
    ''' The time out of an activity '''
    def __init__(self, details=None):
        super(ActivityTimedOut, self).__init__()
        self.details = details

    def __repr__(self):
        return 'ActivityTimedOut(%s)' % self.details