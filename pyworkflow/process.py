class Process(object):
    """
    Insight: Processes may need to contain execution state in order for 
    backends to take action. Backends may override this class to provide that state.
    """

    def __init__(self, pid, workflow, input=None, parent=None):
    	self._id = pid
        self._workflow = workflow
        self._input = input

    @property
    def id(self):
    	return self._id

    @property
    def workflow(self):
    	return self._workflow

    @property
	def parent(self):
		return self._parent

	@property
	def input(self):
		return self._input

	@property
	def tag(self):
		return str(self.input)

class Event(object):
	def __init__(self, activity, state):
		self.activity = activity
		self.state = state