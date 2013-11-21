class DecisionWorker():
    """
    Make decisions provided by the WorkflowManager
    """

    def __init__(self, manager):
        self.manager = manager

    def decide(self, task, workflow):
        decisions = workflow.decide(task.process)

        # Convert Activity results to ScheduleActivity decisions
        def convert(decision):
            if isinstance(decision, Activity):
                return ScheduleActivity(activity=decision, input=task.process.input)
            else:
                return decision

        # Make sure we return a list
        return map(convert, decisions if hasattr(decisions, '__iter__') else [decisions])

    def run(self):
        while not self.stopped:
            task = self.manager.next_decision()
            if task:
                workflow = self.manager.workflow_for_task(task)
                decisions = self.decide(task, workflow)
                self.manager.complete_task(task, decisions)