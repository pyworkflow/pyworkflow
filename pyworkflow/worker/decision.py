class DecisionWorker():
    """
    Make decisions provided by the WorkflowManager
    """

    def __init__(self, manager):
        self.manager = manager

    def decide(self, task, workflow):
        decisions = workflow.decide(task.process)

        # Make sure we return a list
        if not type(decisions) is list:
            decisions = [decisions]

        # Convert Activity results to ScheduleActivity decisions
        for idx,decision in enumerate(decisions):
            if isinstance(decision, Activity):
                decisions[idx] = ScheduleActivity(activity=decision, input=task.process.input)

        return decisions

    def run(self):
        while not self.stopped:
            (task, workflow) = self.manager.next_decision()
            if task:
                decisions = self.decide(task, workflow)
                self.manager.complete_task(task, decisions)