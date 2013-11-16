import json

from ...task import DecisionTask, ActivityTask
from .process import AmazonSWFProcess

class AmazonSWFDecisionTask(DecisionTask):
    def __init__(self, token, process):
        super(AmazonSWFDecisionTask, self).__init__(process)
        self.token = token

    @staticmethod
    def from_description(description):
        token = description.get('taskToken', None)

        process = AmazonSWFProcess.from_description(description)
        return AmazonSWFDecisionTask(token, process)

class AmazonSWFActivityTask(ActivityTask):
    def __init__(self, token, *args, **kwargs):
        super(AmazonSWFActivityTask, self).__init__(*args, **kwargs)
        self.token = token

    @staticmethod
    def from_description(description):
        token = description.get('taskToken', None)
        activity = description['activityType']['name']
        workflow = description.get('workflowType', {}).get('name', None)
        input = json.loads(description.get('input')) if description.get('input', None) else None
        return AmazonSWFActivityTask(token, activity, input)