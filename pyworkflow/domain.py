from .backend import Backend

class Domain(object):
    """
    Handles the creation and execution of workflows, 
    similar to the way a datastore Manager handles a datastore.

    # Create an instance of a task using a workflow manager
    mgr = manager(backend, workflows)
    obj = Workflow()
    mgr.start(obj)

    # Query an activity, execute and set result, and commit using workflow manager
    obj = mgr.next()
    obj.result = activity(obj)
    mgr.commit(obj)
    """

    def __init__(self, backend, workflows):
        self.backend = backend
        self.activities = []
        self.workflows = []

        for workflow in workflows:
            self._register_workflow(workflow)

    def _register_workflow(self, workflow):
        for activity in workflow.activities:
            self.activities[activity.name] = activity
            self.backend.register_activity(activity)

        self.workflows[workflow.name] = workflow
        self.backend.register_workflow(workflow.name)

    def workflow(self, name):
        return self.workflows.get(name, None)

    def activity(self, name):
        return self.activities.get(name, None)

    def start_workflow(self, workflow_cls, input=None):
        if input and not not isinstance(input, ProcessInput):
            raise ValueError('Expected input of type ProcessInput')

        self.backend.start_workflow(workflow_cls.name, input=input)

    def signal_workflows(self, signal, workflow_cls, input, min_datetime=None):
        processes = self.backend.list_processes(workflow_cls.name, input.tag, min_datetime)
        for process in processes:
            self.backend.signal_process(process, signal)
