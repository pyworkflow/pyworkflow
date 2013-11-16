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
        self.activities = {}
        self.workflows = {}

        for workflow in workflows:
            self.register_workflow(workflow)

    def register_workflow(self, workflow):
        for activity in workflow.activities:
            self.register_activity(activity)

        conf = {
            'timeout': workflow.timeout
        }

        self.workflows[workflow.name] = workflow
        self.backend.register_workflow(workflow.name, **conf)

    def register_activity(self, activity):
        conf = {
            'category': activity.category,
            'scheduled_timeout': activity.scheduled_timeout,
            'execution_timeout': activity.execution_timeout,
            'heartbeat_timeout': activity.heartbeat_timeout
        }

        self.activities[activity.name] = activity
        self.backend.register_activity(activity.name, **conf)
        
    def start_process(self, process):
        self.backend.start_process(process)

    def signal_process(self, process, signal):
        self.backend.signal_process(process, signal.name, signal.data)

    def processes(self):
        return self.backend.processes()

    def next_decision(self):
        task = self.backend.poll_decision_task()
        if task:
            workflow_cls = self.workflows[task.process.workflow]
            return (task, workflow_cls())

    def next_activity(self):
        task = self.backend.poll_activity_task()
        if task:
            activity_cls = self.activities[task.activity]
            return (task, activity_cls(task.input))

    def complete_task(self, task, result):
        if isinstance(task, DecisionTask):
            self.backend.complete_decision_task(task, result)
        elif isinstance(task, ActivityTask):
            self.backend.complete_activity_task(task, result)
        else:
            raise ValueError('unsupported task type')