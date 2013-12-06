class Task(object):
	pass

class ActivityTask(Task):
	def __init__(self, activity, input=None, context=None, process_id=None):
		super(ActivityTask, self).__init__()

		self.activity = activity
		self.input = input
		self.context = context or {}
		self.process_id = process_id

	def __repr__(self):
		return 'ActivityTask(%s, %s, %s, %s)' % (self.activity, self.input, self.context, self.process_id)

class DecisionTask(Task):
	def __init__(self, process, context=None):
		super(DecisionTask, self).__init__()

		self.context = context or {}
		self.process = process
	
	def __repr__(self):
		return 'DecisionTask(%s)' % (self.process)