class Decision(object):
	pass

class CompleteProcess(Decision):
	pass

class TerminateProcess(Decision):
	pass

class ScheduleActivity(Decision):
	def __init__(self, activity, activity_version=None, category=None, input=None):
		self.activity = activity
		self.activity_version = activity_version
		self.category = category
		self.input = input