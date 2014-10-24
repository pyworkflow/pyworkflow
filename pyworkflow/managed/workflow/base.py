from ...defaults import Defaults
from ...util import classproperty

class Workflow(object):
    """ 
    Business logic that ties activities together. Core lies in decide() which commands
    the execution flow of a workflow task. It returns either an activity to execute
    or signals the task to be completed or terminated.
    """
    activities = []
    timeout = Defaults.WORKFLOW_TIMEOUT
    decision_timeout = Defaults.DECISION_TIMEOUT
    category = Defaults.DECISION_CATEGORY

    @classproperty
    def name(cls):
        name = cls.__name__
        if name.endswith('Workflow') and len(name) > 8:
            return name[:-8]
        return name
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def decide(self, process):
        ''' Take the next decision for the process in this workflow '''
        raise NotImplementedError()