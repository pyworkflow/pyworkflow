import traceback
from uuid import uuid4
from ...activity import ActivityResult, ActivityCompleted, ActivityCanceled, ActivityFailed
from ..activity import ActivityMonitor

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

    def _log_msg(self, head, task, result=None, include_task=False):
        activity = task.activity_execution.activity
        task_id = task.activity_execution.id

        msg = '%s %s activity (%s)' % (head, activity, task_id)
        
        if include_task:
            msg += '\nTask: %s' % task
        if result:
            msg += '\nResult: %s' % result

        return msg

    def log_result(self, task, result, logger):
        if isinstance(result, ActivityCompleted):
            logger.info(self._log_msg('Completed', task, result))
        elif isinstance(result, ActivityCanceled):
            logger.info(self._log_msg('Aborted', task, result))
        elif isinstance(result, ActivityFailed):
            logger.warning(self._log_msg('Failed', task, result, include_task=True))
        elif result is None:
            logger.info(self._log_msg('Handed off', task, result))
        
    def step(self, logger=None):
        # Rely on the backend poll to be blocking
        task = self.manager.next_activity(identity=self.name)
        if task:
            if logger:
                logger.info(self._log_msg('Starting', task, None, include_task=True))
            try:
                activity = self.manager.activity_for_task(task, monitor=self.monitor_for_task(task))
                result = self.execute_activity(activity)

                if result:
                    self.manager.complete_task(task, result)

            except Exception, e:
                logger.info(self._log_msg('Error in', task, str(e), include_task=True))
                return True # we consumed a task
            
            if logger:
                self.log_result(task, result, logger)            

            return True

    def __repr__(self):
        return 'ActivityWorker(%s, %s)' % (self.manager, self.name)