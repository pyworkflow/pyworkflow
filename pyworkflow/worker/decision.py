from uuid import uuid4
from ..activity import Activity

class DecisionWorker(object):
    """
    Make decisions provided by the WorkflowManager
    """

    def __init__(self, manager, name=None):
        self.manager = manager
        self.name = name or str(uuid4())

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

    def step(self, logger=None):
        task = self.manager.next_decision(identity=self.name)
        if task:
            if logger:
                logger.info("Worker %s: Starting %s" % (self.name, task))

            workflow = self.manager.workflow_for_task(task)
            decisions = self.decide(task, workflow)

            if logger:
                logger.info("Worker %s: Completed %s: %s" % (self.name, task, decisions))

            self.manager.complete_task(task, decisions)

    def __repr__(self):
        return 'DecisionWorker(%s, %s)' % (self.manager, self.name)