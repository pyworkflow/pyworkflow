from .backend import Backend

class Manager(object):
    """
    Handles the creation and execution of workflows, 
    similar to the way a datastore Manager handles a datastore.

    # Create an instance of a model using a datastore manager
    mgr = manager(ds, model)
    obj = model()
    mgr.put(obj)

    # Query an object, set a result, and save it using datastore manager
    obj = mgr.query()
    obj.result = activity(obj)
    mgr.put(obj)

    # Create an instance of a task using a workflow manager
    mgr = manager(backend, workflows)
    obj = Workflow()
    mgr.start(obj)

    # Query an activity, execute and set result, and commit using workflow manager
    obj = mgr.next()
    obj.result = activity(obj)
    mgr.commit(obj)
    """

    def __init__(self, backend):
        self.backend = backend

    def register_workflow(self, workflow):
        for activity in workflow.activities:
            self.backend.register_activity(activity)

        self.backend.register_workflow(workflow)