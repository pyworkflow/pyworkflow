class Task(object):
	def __init__(self, process):
		self.process = process

class ActivityTask(object):
	def __init__(self, process, activity):
		super(ActivityTask, self).__init__(process)
		self.activity = activity

class DecisionTask(object):
	def __init__(self, process, history):
		super(DecisionTask, self).__init__(process)
		self.history = history