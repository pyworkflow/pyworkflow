class ActivityExecutionContext(object):
	''' 
	Context used for Activity to execute. 
	Allows some controlled communication with invoker of Activity.execute().
	'''

	def __init__(self, heartbeat_fn=pass):
		self.heartbeat = heartbeat_fn