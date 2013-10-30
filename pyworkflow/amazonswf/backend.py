from .. import Backend, ActivityTask, DecisionTask
from process import AmazonSWFProcess

class AmazonSWFBackend(Backend):
    def __init__(self, domain):
        self.domain = domain

    def register_workflow(self, workflow):
        self.workflows[workflow.name] = workflow
        swf.register_workflow(workflow)

    def register_activity(self, activity):
        self.activities[activity.name] = activity
        swf.register_activity(activity)

    def start_process(self, workflow, input):
        raise NotImplementedError()

    def signal_process(self, pid, signal):
        raise NotImplementedError()     

    def complete_process(self, pid):
        raise NotImplementedError()

    def cancel_process(self, pid):
        swf.terminate_workflow_execution(pid)

    def processes(self, workflow=None, input=None, after_date=None):
        swf.list_open_workflow_executions(domain, after_date, workflow_name=workflow.name, tag=input.tag)

    def poll_activity_task(self):
        task = ActivityWorker().poll()
        return ActivityTask(AmazonSWFProcess(task.token, task.id, task.input), task.activity)

    def poll_decision_task(self):
        task = Decider().poll()
        return DecisionTask(AmazonSWFProcess(task.token, task.id, task.input), task.history)

    def schedule_activity(self, process, input):
        if not isinstace(process, AmazonSWFProcess):
            raise ValueError('Can only act on AmazonSWFProcess')

    def complete_activity(self, process, result):
        if not isinstace(process, AmazonSWFProcess):
            raise ValueError('Can only act on AmazonSWFProcess')

        ActivityWorker().complete(token=process.token, result=result)

    def abort_activity(self, process, reason):
        if not isinstace(process, AmazonSWFProcess):
            raise ValueError('Can only act on AmazonSWFProcess')

        ActivityWorker().abort(token=process.token, reason=result)

    def fail_activity(self, process, error):
        if not isinstace(process, AmazonSWFProcess):
            raise ValueError('Can only act on AmazonSWFProcess')

        ActivityWorker().fail(token=process.token, error=result)