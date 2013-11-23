import itertools
from backend import Backend
from task import DecisionTask, ActivityTask

class Manager(object):
    """
    Handles the creation and execution of workflows.

    # Start a new process
    mgr = manager(backend, workflows)
    process = Process()
    mgr.start_process(process)

    # Query an activity, execute and commit result
    task = mgr.next()
    result = activity(task)
    mgr.complete_task(task, result)
    """

    def __init__(self, backend, workflows=[]):
        self._backend = backend
        
        self._workflows = dict((workflow.name, workflow) for workflow in workflows)
        activities = itertools.chain(*map(lambda w: w.activities, workflows))
        self._activities = dict((a.name, a) for a in activities)

        map(self._register_workflow_with_backend, workflows)
        map(self._register_activity_with_backend, activities)

    def _register_workflow_with_backend(self, workflow):
        conf = {
            'timeout': workflow.timeout
        }

        self._backend.register_workflow(workflow.name, **conf)

    def _register_activity_with_backend(self, activity):
        conf = {
            'category': activity.category,
            'scheduled_timeout': activity.scheduled_timeout,
            'execution_timeout': activity.execution_timeout,
            'heartbeat_timeout': activity.heartbeat_timeout
        }

        self._backend.register_activity(activity.name, **conf)
        
    def start_process(self, process):
        self._backend.start_process(process)

    def signal_process(self, process, signal):
        self._backend.signal_process(process, signal.name, signal.data)

    def heartbeat(self, task):
        self._backend.heartbeat(task)

    def processes(self):
        return self._backend.processes()

    def next_decision(self, identity=None):
        return self._backend.poll_decision_task(identity=identity)

    def next_activity(self, identity=None):
        return self._backend.poll_activity_task(identity=identity)

    def workflow_for_task(self, task):
        workflow_cls = self._workflows[task.process.workflow]
        return workflow_cls()

    def activity_for_task(self, task, monitor=None):
        activity_cls = self._activities[task.activity]
        return activity_cls(task.input, monitor)

    def complete_task(self, task, result):
        if isinstance(task, DecisionTask):
            self._backend.complete_decision_task(task, result)
        elif isinstance(task, ActivityTask):
            self._backend.complete_activity_task(task, result)
        else:
            raise ValueError('unsupported task type')

    def copy_with_backend(self, backend):
        return Manager(backend, self._workflows.values())

    def __repr__(self):
        return 'Manager(%s)' % self._backend.__class__.__name__