from defaults import Defaults

class Backend(object):
    def register_workflow(self, name, version="1.0", timeout=Defaults.WORKFLOW_TIMEOUT, decision_timeout=Defaults.DECISION_TIMEOUT):
        raise NotImplementedError()

    def register_activity(self, name, version="1.0", category="default", scheduled_timeout=Defaults.ACTIVITY_SCHEDULED_TIMEOUT, execution_timeout=Defaults.ACTIVITY_EXECUTION_TIMEOUT, heartbeat_timeout=Defaults.ACTIVITY_HEARTBEAT_TIMEOUT):
        raise NotImplementedError()

    def process_by_id(self, pid):
        raise NotImplementedError()

    def processes(self, workflow=None, tag=None):
        raise NotImplementedError()     
    
    def start_process(self, process):
        raise NotImplementedError()
    
    def signal_process(self, process, signal, data=None):
        raise NotImplementedError()

    def cancel_process(self, process, details=None):
        raise NotImplementedError()

    def poll_activity_task(self, category=Defaults.ACTIVITY_CATEGORY, identity=None):
        raise NotImplementedError()

    def poll_decision_task(self, identity=None):
        raise NotImplementedError()

    def heartbeat_activity_task(self, task):
        raise NotImplementedError()

    def complete_decision_task(self, task, decisions):
        raise NotImplementedError()

    def complete_activity_task(self, task, result=None):
        raise NotImplementedError()