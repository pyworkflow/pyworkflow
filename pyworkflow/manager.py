from backend import Backend
from task import DecisionTask, ActivityTask

class Manager(object):
    """
    Handles the creation and execution of workflows.

    # Create an instance of a task using a workflow manager
    mgr = manager(backend, workflows)
    process = Process()
    mgr.start(process)

    # Query an activity, execute and set result, and commit using workflow manager
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
            self.activities[activity.name] = activity
            self.backend.register_activity(activity.name)

        self.workflows[workflow.name] = workflow
        self.backend.register_workflow(workflow.name)

    def start_process(self, process):
        self.backend.start_process(process)

    #def signal_processes(self, signal, workflow_cls, input, min_datetime=None):
    #    processes = self.backend.list_processes(workflow_cls.name, input.tag, min_datetime)
    #    for process in processes:
    #        self.backend.signal_process(process, signal)

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