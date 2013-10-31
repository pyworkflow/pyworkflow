from time import sleep
from activity.context import ActivityExecutionContext

class ActivityWorker(object):
    """
    Executes activities provided by the WorkflowManager
    """

    def __init__(self, domain):
        self.domain = domain

    def activity_for_task(self, task):
        activity_cls = self.domain.activity(task.activity)
        if not activity_cls:
            raise Exception('Task specified unknown activity %s' % task.activity)

        return activity_cls()

    def context_for_task(self, task):
        heartbeat_fn = lambda: self.domain.backend.heartbeat(task)
        return ActivityExecutionContext(heartbeat_fn)

    def execute_task(self, task):
        activity = self.activity_for_task(task)
        context = self.context_for_task(task)

        try:
            result = activity.execute(task.input, context)
            self.domain.backend.complete_activity_task(task, result=result)
        except ActivityAbortion, a:
            self.domain.backend.abort_activity_task(task, reason=a.reason)
        except ActivityFailure, f:
            self.domain.backend.fail_activity_task(task, error=f.error, reason=f.reason)
        except Exception, e:
            self.domain.backend.fail_activity_task(task, error=e, reason=str(e))

    def run(self):
        while not self.stopped:
            # Rely on the backend poll to be blocking
            task = self.domain.backend.poll_activity_task()
            if task:
                self.execute_task(task)