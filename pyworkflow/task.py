class Task(object):
	def __init__(self, process):
		self.process = process

class ActivityTask(Task):
	def __init__(self, process, activity, input):
		super(ActivityTask, self).__init__(process)
		self.activity = activity
		self.input = input

class ActivityResult(object):
	pass

class ActivityCompleted(ActivityResult):
	def __init__(self, result=None):
		self.result = result

class ActivityAborted(ActivityResult):
	''' The abortion of an activity '''
	def __init__(self, details=None):
		self.details = details

class ActivityFailed(ActivityResult):
	''' The failure of an activity '''
	def __init__(self, details=None, error=None):
		self.details = details
		self.error = error

class DecisionTask(Task):
	def __init__(self, process):
		super(DecisionTask, self).__init__(process)

class Decision(object):
	pass

class CompleteProcess(Decision):
	def __init__(self, result=None):
		self.result = result

class TerminateProcess(Decision):
	pass

class ScheduleActivity(Decision):
	def __init__(self, activity, activity_version=None, category=None, input=None):
		self.activity = activity
		self.activity_version = activity_version
		self.category = category
		self.input = input