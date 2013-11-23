class Task(object):
	pass

class ActivityTask(Task):
	def __init__(self, activity, input=None):
		super(ActivityTask, self).__init__()

		self.activity = activity
		self.input = input

	def __repr__(self):
		return 'ActivityTask(%s, %s)' % (self.activity, self.input)

class DecisionTask(Task):
	def __init__(self, process):
		super(DecisionTask, self).__init__()

		self.process = process
	
	def __repr__(self):
		return 'DecisionTask(%s)' % (self.process)