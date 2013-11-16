from ..util import classproperty
from .. import Defaults

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

    def __init__(self, input=None, monitor=None):
        self._input = input
        self._monitor = monitor

    @property
    def monitor(self):
        return self._monitor

    @monitor.setter
    def monitor(self, monitor):
        self._monitor = monitor

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, input):
        self._input = input

    def heartbeat(self):
        ''' sends a heart beat to the monitor '''
        if self._monitor:
            self._monitor.heartbeat()

    def execute(self):
        raise NotImplementedError()

class ActivityExecution(object):
    def __init__(self, name, id, input=None):
        self.name = name
        self.id = id
        self.input = input

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return 'ActivityExecution(%s, %s, %s)' % (self.name, self.id, self.input)