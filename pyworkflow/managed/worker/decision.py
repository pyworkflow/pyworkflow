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

    def _log_msg(self, head, task, result=None, include_task=False):
        workflow_name = task.process.workflow
        process_id = task.process.id

        msg = '%s %s decision (%s)' % (head, workflow_name, process_id)

        if include_task:
            msg += '\nTask: %s' % task
        if result:
            msg += '\nResult: %s' % result

        return msg

    def step(self, logger=None):
        task = self.manager.next_decision(identity=self.name)
        if task:
            if logger:
                logger.info(self._log_msg("Starting", task, None, include_task=True))

            workflow = self.manager.workflow_for_task(task)
            decisions = None
            try:
                decisions = self.decide(task, workflow)
                self.manager.complete_task(task, decisions)
            except Exception, e:
                logger.exception(self._log_msg("Error in", task, 'Exception: %s\nDecisions: %s' % (str(e), str(decisions)), include_task=True))
                return True # we consumed a task
            
            if logger:
                logger.info(self._log_msg("Completed", task, decisions))

            return True # we consumed a task

    def __repr__(self):
        return 'DecisionWorker(%s, %s)' % (self.manager, self.name)