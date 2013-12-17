from uuid import uuid4
from ..activity import Activity
from ...decision import Decision, ScheduleActivity

class DecisionWorker(object):
    """
    Make decisions provided by the WorkflowManager
    """

    def __init__(self, manager, name=None):
        self.manager = manager
        self.name = name or str(uuid4())

    def decide(self, task, workflow):
        decisions = workflow.decide(task.process)
        if not decisions:
            return []

        # Convert Activity results to ScheduleActivity decisions
        def convert(decision):
            if type(decision) is type and issubclass(decision, Activity):
                return ScheduleActivity(activity=decision, input=task.process.input)
            elif isinstance(decision, Decision):
                return decision
            else:
                raise ValueError('Invalid decision type: %s', type(decision))

        # Make sure we return a list
        return map(convert, decisions if hasattr(decisions, '__iter__') else [decisions])

    def step(self, logger=None):
        task = self.manager.next_decision(identity=self.name)
        if task:
            if logger:
                logger.info("Worker %s: Starting %s" % (self.name, task))

            workflow = self.manager.workflow_for_task(task)
            try:
                decisions = self.decide(task, workflow)
            except Exception, e:
                logger.exception("Worker %s: Error in decision task %s: %s" % (self.name, task, str(e)))
                return True # we consumed a task
            
            if logger:
                logger.info("Worker %s: Completed %s with result %s" % (self.name, task, decisions))

            self.manager.complete_task(task, decisions)

            return True # we consumed a task

    def __repr__(self):
        return 'DecisionWorker(%s, %s)' % (self.manager, self.name)