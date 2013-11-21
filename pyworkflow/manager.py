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
        self.backend = backend
        
        self.workflows = dict((workflow.name, workflow) for workflow in workflows)
        activities = itertools.chain(*map(lambda w: w.activities, workflows))
        self.activities = dict((a.name, a) for a in activities)

        map(self._register_workflow_with_backend, workflows)
        map(self._register_activity_with_backend, activities)

    def _register_workflow_with_backend(self, workflow):
        conf = {
            'timeout': workflow.timeout
        }

        self.backend.register_workflow(workflow.name, **conf)

    def _register_activity_with_backend(self, activity):
        conf = {
            'category': activity.category,
            'scheduled_timeout': activity.scheduled_timeout,
            'execution_timeout': activity.execution_timeout,
            'heartbeat_timeout': activity.heartbeat_timeout
        }

        self.backend.register_activity(activity.name, **conf)
        
    def start_process(self, process):
        self.backend.start_process(process)

    def signal_process(self, process, signal):
        self.backend.signal_process(process, signal.name, signal.data)

    def processes(self):
        return self.backend.processes()

    def next_decision(self):
        return self.backend.poll_decision_task()

    def next_activity(self):
        return self.backend.poll_activity_task()

    def workflow_for_task(self, task):
        workflow_cls = self.workflows[task.process.workflow]
        return workflow_cls()

    def activity_for_task(self, task, monitor=None):
        activity_cls = self.activities[task.activity]
        return activity_cls(task.input, monitor)

    def complete_task(self, task, result):
        if isinstance(task, DecisionTask):
            self.backend.complete_decision_task(task, result)
        elif isinstance(task, ActivityTask):
            self.backend.complete_activity_task(task, result)
        else:
            raise ValueError('unsupported task type')