class Decider():
    """
    Make decisions provided by the WorkflowManager
    """

    def __init__(self, manager):
        self.manager = manager

    def schedule_activity(self, task, activity):
        self.backend.schedule_activity(task, activity)

    def complete_task(self, task):
        self.backend.complete_task(task)

    def run(self):
        while not self.stopped:
            decision_task = self.manager.poll_decision_task()

            workflow = self.manager.workflow_by_name(decision.workflow)
            decision = workflow.decide(decision_task)

            self.manager.complete_decision(decision)