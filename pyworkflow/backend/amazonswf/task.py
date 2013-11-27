import json

from ...activity import ActivityExecution
from ...task import DecisionTask, ActivityTask
from .process import AmazonSWFProcess

def decision_task_from_description(description):
    token = description.get('taskToken', None)
    if not token:
        return None

    process = AmazonSWFProcess.from_description(description)
    return DecisionTask(process, context={'token': token})

def activity_task_from_description(description):
    token = description.get('taskToken', None)
    if not token:
        return None

    activity_id = description['activityId']
    activity = description['activityType']['name']
    input = json.loads(description.get('input')) if description.get('input', None) else None

    return ActivityTask(activity=activity, input=input, context={'token': token})