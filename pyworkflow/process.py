from uuid import uuid4

class Process(object):
    """
    Insight: Processes may need to contain execution state in order for 
    backends to take action. Backends may override this class to provide that state.
    """

    def __init__(self, pid=None, workflow=None, workflow_version=None, input=None, history=None, parent=None):
        self.id = pid or str(uuid4())
        self.workflow = workflow
        self.workflow_version = workflow_version
        self.input = input
        self.history = []

    @property
    def tag(self):
        return str(self.input)

class Event(object):
    def __init__(self, activity, state):
        self.activity = activity
        self.state = state