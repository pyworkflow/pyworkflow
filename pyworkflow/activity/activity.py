from ..util import classproperty

class Activity(object):
    '''
    Implementation of a certain activity. Operates just on a task input and returns result.
    Contains some configuration properties on the class

    Pretty much independent from any other workflow classes, except an ActivityExecutionContext
    is supplied on execution to allow communication to the invoker (e.g. heartbeats).
    '''

    scheduled_timeout = None
    execution_timeout = None
    heartbeat_timeout = None

    auto_complete = True
    task_list = None

    @classproperty
    def name(cls):
        name = cls.__name__
        if name.endswith('Activity'):
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
        if self._monitor:
            self._monitor.heartbeat()

    def execute(self):
        raise NotImplementedError()