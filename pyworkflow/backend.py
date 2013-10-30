class Backend(object):
	def register_workflow(self, workflow):
		raise NotImplementedError()

	def register_activity(self, activity):
		raise NotImplementedError()

	def start_process(self, workflow, input):
		raise NotImplementedError()

	def signal_process(self, pid, signal):
		raise NotImplementedError()		

	def complete_process(self, pid):
		raise NotImplementedError()

	def cancel_process(self, pid):
		raise NotImplementedError()

	def schedule_activity(self, process, input):
		raise NotImplementedError()

	def complete_activity(self, process, result):
		raise NotImplementedError()

	def abort_activity(self, workflow, reason):
		raise NotImplementedError()

	def fail_activity(self, workflow, error):
		raise NotImplementedError()

	def poll_activity_task(self):
		raise NotImplementedError()

	def poll_decision_task(self):
		raise NotImplementedError()