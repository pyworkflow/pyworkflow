class ActivityAborted(Exception):
	''' The abortion of an activity '''
	def __init__(self, reason=None):
		self.reason = reason

class ActivityFailed(Exception):
	''' The failure of an activity '''
	def __init__(self, error=None, details=None):
		self.error = error
		self.details = details