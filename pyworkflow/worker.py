class ActivityWorker(object):
    """
    Executes activities provided by the WorkflowManager
    """

    def __init__(self, domain):
        self.domain = domain

    def run(self):
        while not self.stopped:
            task = self.domain.poll_activity_task()
            if task:
                activity = self.domain.activity_by_name(task.activity)

                try:
                    result = activity.execute(task.input)
                    self.domain.complete_activity(activity, result)
                except Exception, e:
                    self.domain.fail_activity(activity, e)

