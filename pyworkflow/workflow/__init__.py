class Workflow(object):
    """ 
    Business logic that ties activities together. Core lies in decide() which commands
    the execution flow of a workflow task. It returns either an activity to execute
    or signals the task to be completed or terminated.
    """
    activities = []
    
    @classmethod
    def decide(cls, process):
    	''' Take decisions for the process given its history '''
        raise NotImplementedError()
