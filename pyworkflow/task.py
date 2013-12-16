class Task(object):
	pass

class ActivityTask(Task):
	def __init__(self, activity_execution, process_id=None, context=None):
		super(ActivityTask, self).__init__()

		self.activity_execution = activity_execution
		self.process_id = process_id
		self.context = context or {}

	def __repr__(self):
		return 'ActivityTask(%s, %s)' % (self.activity_execution, self.process_id)

class DecisionTask(Task):
	def __init__(self, process, context=None):
		super(DecisionTask, self).__init__()

		self.process = process
		self.context = context or {}
	
	def __repr__(self):
		return 'DecisionTask(%s)' % (self.process)