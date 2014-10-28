import itertools
from ..task import DecisionTask, ActivityTask
from ..events import ProcessStartedEvent
from ..defaults import Defaults

class Manager(object):
    """
    Handles the creation and execution of workflows.

    # Start a new process
    mgr = manager(backend, workflows)
    process = Process(workflow=FooWorkflow, tags=["foo", "bar"])
    mgr.start_process(process)

    # Find the process
    mgr.processes(workflow=FooWorkflow, tag="foo")

    # Query an activity, execute and commit result
    task = mgr.next()
    result = activity(task)
    mgr.complete_task(task, result)
    """

    def __init__(self, backend, workflows=[]):
        self._backend = backend
        
        self._workflows = dict((workflow.name, workflow) for workflow in workflows)
        activities = list(itertools.chain(*map(lambda w: w.activities, workflows)))
        self._activities = dict((a.name, a) for a in activities)

        map(lambda w: self._register_workflow_with_backend(w), workflows)
        map(lambda a: self._register_activity_with_backend(a), activities)

    def _register_workflow_with_backend(self, workflow):
        kwargs = {
            'category': workflow.category,
            'timeout': workflow.timeout,
            'decision_timeout': workflow.decision_timeout
        }

        self._backend.register_workflow(workflow.name, **kwargs)

    def _register_activity_with_backend(self, activity):
        kwargs = {
            'category': activity.category,
            'scheduled_timeout': activity.scheduled_timeout,
            'execution_timeout': activity.execution_timeout,
            'heartbeat_timeout': activity.heartbeat_timeout
        }

        self._backend.register_activity(activity.name, **kwargs)
        
    def start_process(self, process):
        return self._backend.start_process(process)

    def signal_process(self, process_or_id, signal):
        process_id = getattr(process_or_id, 'id', process_or_id)
        self._backend.signal_process(process_id, signal.name, signal.data)

    def cancel_process(self, process_or_id, details=None):
        process_id = getattr(process_or_id, 'id', process_or_id)
        self._backend.cancel_process(process_id, details=details)

    def heartbeat(self, task):
        self._backend.heartbeat_activity_task(task)

    def process_by_id(self, process_id):
        return self._backend.process_by_id(process_id)

    def processes(self, workflow=None, tag=None):
        workflow_name = None
        if workflow:
            workflow_name = workflow.name if hasattr(workflow, 'name') else str(workflow)
        
        return self._backend.processes(workflow=workflow_name, tag=tag)

    def next_decision(self, identity=None, category=Defaults.DECISION_CATEGORY):
        return self._backend.poll_decision_task(identity=identity, category=category)

    def next_activity(self, identity=None, category=Defaults.ACTIVITY_CATEGORY):
        return self._backend.poll_activity_task(identity=identity, category=category)

    def workflow_for_task(self, task):
        workflow_cls = self._workflows[task.process.workflow]
        return workflow_cls()

    def activity_for_task(self, task, monitor=None):
        activity_cls = self._activities[task.activity_execution.activity]
        return activity_cls(task=task, monitor=monitor)

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