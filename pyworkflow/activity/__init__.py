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

    @classmethod
    def execute(cls, input, context):
        raise NotImplementedError()