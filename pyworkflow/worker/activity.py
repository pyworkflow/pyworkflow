from time import sleep
from ..activity import ActivityMonitor

class ActivityWorker(object):
    """
    Executes activities provided by the WorkflowManager
    """

    def __init__(self, manager):
        self.manager = manager

    def monitor_for_task(self, task):
        heartbeat_fn = lambda: self.manager.backend.heartbeat(task)
        return ActivityMonitor(heartbeat_fn)

    def execute_task(self, task, activity):
        activity.monitor = self.monitor_for_task(task)

        try:
            result = activity.execute()
            return ActivityCompleted(result)
        except ActivityAborted, a:
            return a
        except ActivityFailed, f:
            return f
        except Exception, e:
            return ActivityFailed(e, str(e))

    def run(self):
        while not self.stopped:
            # Rely on the backend poll to be blocking
            (task, activity) = self.manager.next_activity()
            if task:
                result = self.execute_task(task, activity)
                self.manager.complete_task(task, result)