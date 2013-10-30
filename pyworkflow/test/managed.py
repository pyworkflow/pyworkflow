from .. import Activity
from .. import Workflow

class ApplicantDocumentCollectionActivity(Activity):
    """
    Example of specific activity that signals parent task
    """

    @classmethod
    def operand(cls, task):
        return Applicant.get(task.process.input['id'])
        
    @classmethod
    def execute(cls, task, manager):
        manager.heartbeat(task)

        # kick parent application process back into collection if it was in verification already
        manager.signal(task.process.parent, ABORT_VERIFICATION)

class ApplicationDocumentCollectionActivity(Activity):
    """
    Example of specific activity that starts child task
    """
    
    @classmethod
    def operand(cls, task):
        return Application.get(task.process.input['id'])

    @classmethod
    def execute(cls, task, manager):
        application = cls.operand(task)

        # start applicant workflows
        for applicant in application.applicants:
            manager.start(ApplicantWorkflow, applicant.workflow_input)

class ApplicantWorkflow(Workflow):
    activities = [ApplicantDocumentCollectionActivity]
    
    @classmethod
    def decide(cls, task):
        return ActivityDecision(ApplicantDocumentCollectionActivity)

class ApplicationWorkflow(Workflow):
    activities = [ApplicationDocumentCollectionActivity]

    @classmethod
    def decide(cls, task):
        if task.history.last_signal == ABORT_VERIFICATION and task.history.current_activity == COLLECTION:
            return ABORT

        if task.history.last_activity == COLLECTION and task.history.last_decision == ABORT:
            return ApplicationDocumentCollectionActivity


domain = WorkflowDomain(backend=DatastoreBackend(DictDatastore()))
domain.register([
    ApplicantWorkflow,
    ApplicationWorkflow
])

domain.start(workflow=ApplicantWorkflow, input=123, parent=456)
domain.signal(workflow=ApplicantWorkflow, input=123, signal=ABORT)


