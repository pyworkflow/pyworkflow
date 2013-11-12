class ActivityMonitor(object):
    ''' 
    Responds to events from activity
    Allows some controlled communication between Activity and its invoker.
    '''

    def __init__(self, heartbeat_fn=None):
    	def noop():
    		pass

        self.heartbeat = heartbeat_fn or noop
