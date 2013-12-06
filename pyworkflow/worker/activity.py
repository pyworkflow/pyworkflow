import traceback
from uuid import uuid4
from ..activity import ActivityResult, ActivityCompleted, ActivityCanceled, ActivityFailed, ActivityMonitor

class ActivityWorker(object):
    """
    Executes activities provided by the WorkflowManager
    """

    def __init__(self, manager, name=None):
        self.manager = manager
        self.name = name or str(uuid4())

    def monitor_for_task(self, task):
        heartbeat_fn = lambda: self.manager.heartbeat(task)
        return ActivityMonitor(heartbeat_fn)

    def execute_activity(self, activity):
        try:
            result = activity.execute()

            if isinstance(result, ActivityResult):
                return result
            elif activity.auto_complete:
                return ActivityCompleted(result)

        except ActivityCanceled, a:
            return a
        except ActivityFailed, f:
            return f
        except Exception, e:
            return ActivityFailed(str(e), traceback.format_exc())

    def log_result(self, task, result, logger):
        if isinstance(result, ActivityCompleted):
            logger.info("Worker %s: Completed %s: %s" % (self.name, task, result))
        elif isinstance(result, ActivityCanceled):
            logger.info("Worker %s: Aborted %s: %s" % (self.name, task, result))
        elif isinstance(result, ActivityFailed):
            logger.warning("Worker %s: Failed %s: %s" % (self.name, task, result))
        elif result is None:
            logger.info("Worker %s: Handed off %s" % (self.name, task))
        
    def step(self, logger=None):
        # Rely on the backend poll to be blocking
        task = self.manager.next_activity(identity=self.name)
        if task:
            if logger:
                logger.info("Worker %s: Starting %s" % (self.name, task))

            activity = self.manager.activity_for_task(task, monitor=self.monitor_for_task(task))
            result = self.execute_activity(activity)

            if logger:
                self.log_result(task, result, logger)
        
            if result:
                self.manager.complete_task(task, result)

            return True

    def __repr__(self):
        return 'ActivityWorker(%s, %s)' % (self.manager, self.name)