class Activity():
    """
    Implementation of a certain activity. Operates just on a task input and returns result.

    Pretty much independent from any other workflow classes, except the manager
    is supplied on execution to start / signal other tasks.
    """

    scheduled_timeout = None
    execution_timeout = None
    heartbeat_timeout = None

    task_list = None

    @classmethod
    def execute(self, task):
        raise NotImplementedError()