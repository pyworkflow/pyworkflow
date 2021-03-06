from ..util import classproperty
from ..defaults import Defaults

class Activity(object):
    '''
    Implementation of a certain activity. Operates just on a task input and returns result.
    Contains some configuration properties on the class

    Pretty much independent from any other workflow classes, except an ActivityMonitor
    can be supplied to allow communication with the invoker (e.g. heartbeats).
    '''

    scheduled_timeout = Defaults.ACTIVITY_SCHEDULED_TIMEOUT
    execution_timeout = Defaults.ACTIVITY_EXECUTION_TIMEOUT
    heartbeat_timeout = Defaults.ACTIVITY_HEARTBEAT_TIMEOUT

    auto_complete = True
    category = Defaults.ACTIVITY_CATEGORY

    @classproperty
    def name(cls):
        ''' the activity name, based on the class name without 'Activity' '''
        name = cls.__name__
        if name.endswith('Activity') and len(name) > 8:
            return name[:-8]
        return name

    def __eq__(self, other):        
        return self.__dict__ == other.__dict__

    def __init__(self, task, monitor=None):
        self._task = task
        self._input = input
        self._monitor = monitor

    @property
    def input(self):
        return self._task.activity_execution.input

    @property
    def task(self):
        return self._task

    @property
    def monitor(self):
        return self._monitor

    def heartbeat(self):
        ''' sends a heart beat to the monitor '''
        if self._monitor:
            self._monitor.heartbeat()

    def execute(self):
        raise NotImplementedError()


class ActivityMonitor(object):
    ''' 
    Responds to events from activity
    Allows some controlled communication between Activity and its invoker.
    '''

    def __init__(self, heartbeat_fn=None):
        def noop():
            pass

        self.heartbeat = heartbeat_fn or noop