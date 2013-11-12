class Backend(object):
    DEFAULT_WORKFLOW_TIMEOUT = 31536000 # 365 days
    DEFAULT_DECISION_TIMEOUT = 60 # 1 minute
    DEFAULT_ACTIVITY_TIMEOUT = 31536000 # 365 days
    DEFAULT_ACTIVITY_HEARTBEAT_TIMEOUT = 3600 # 1 hour

    def register_workflow(self, name, version="1.0", timeout=DEFAULT_WORKFLOW_TIMEOUT):
        raise NotImplementedError()

    def register_activity(self, name, version="1.0", category="default", timeout=DEFAULT_ACTIVITY_TIMEOUT, heartbeat_timeout=DEFAULT_ACTIVITY_HEARTBEAT_TIMEOUT):
        raise NotImplementedError()

    def processes(self):
        raise NotImplementedError()     
    
    def start_process(self, process):
        raise NotImplementedError()
    
    def signal_process(self, process, signal, input=None):
        raise NotImplementedError()

    def cancel_process(self, process, details=None, reason=None):
        raise NotImplementedError()

    def poll_activity_task(self):
        raise NotImplementedError()

    def poll_decision_task(self):
        raise NotImplementedError()

    def complete_decision_task(self, task, decisions):
        raise NotImplementedError()

    def complete_activity_task(self, task, result=None):
        raise NotImplementedError()

class MonitoredBackend(Backend):
    def __init__(self, primary_backend, monitor_backends):
        self.primary = primary_backend
        self.monitors = monitor_backends

    def poll_activity_task(self):
        return self.primary.poll_activity_task()

    def poll_decision_task(self):
        return self.primary.poll_decision_task()