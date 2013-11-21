class Task(object):
	pass

class ActivityTask(Task):
	def __init__(self, activity, input=None):
		super(ActivityTask, self).__init__()

		self.activity = activity
		self.input = input

class DecisionTask(Task):
	def __init__(self, process):
		super(DecisionTask, self).__init__()

		self.process = process