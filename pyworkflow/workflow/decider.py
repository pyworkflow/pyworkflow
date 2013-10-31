from .decision import *

class Decider():
    """
    Make decisions provided by the WorkflowManager
    """

    def __init__(self, backend):
        self.backend = backend

    def workflow_for_task(self, task):
        workflow_cls = self.manager.workflow(task.workflow)
        return workflow_cls()

    def handle_decision(self, task, decision):
        if isinstance(decision, CompleteProcess):
            self.backend.complete_process(task.process)
        elif isinstance(decision, TerminateProcess):
            self.backend.terminate_process(task.process)
        elif isinstance(decision, ScheduleActivity):
            self.backend.schedule_activity(task.process, decision.activity)
        elif isinstance(decision, Activity):
            self.backend.schedule_activity(task.process, activity)
        else:
            raise ValueError('decision must be Activity or Decision')

    def decide(self, task):
        workflow = self.workflow_for_task(task)
        
        decisions = workflow.decide(task.process)
        if not type(decisions) is list:
            decisions = [decisions]

        for decision in decisions:
            self.handle_decision(decision)

    def run(self):
        while not self.stopped:
            task = self.manager.poll_decision_task()
            if task:
                self.decide(task)