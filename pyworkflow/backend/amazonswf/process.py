import json
from datetime import datetime

from ...process import Process
from ...event import Event, DecisionEvent, ActivityEvent
from ...activity import ActivityCompleted, ActivityAborted, ActivityFailed
from ...decision import ScheduleActivity

class AmazonSWFProcess(Process):
    @staticmethod
    def event_from_description(description, related=[]):
        event_type = description['eventType']
        event_dt = datetime.fromtimestamp(description['eventTimestamp'])
        attributes = description.get(event_type[0].lower() + event_type[1:] + 'EventAttributes', {})
            
        def related_activity():
            scheduled_by = filter(lambda x: x['eventId'] == attributes['scheduledEventId'], related)[0]
            return scheduled_by['activityTaskScheduledEventAttributes']['activityType']['name']

        if event_type == 'ActivityTaskScheduled':
            id = attributes['activityId']
            activity = attributes['activityType']['name']
            input = json.loads(attributes['input'])
            return DecisionEvent(datetime=event_dt, decision=ScheduleActivity(id=id, activity=activity, input=input))
        elif event_type == 'ActivityTaskCompleted':
            result = json.loads(attributes['result'])
            return ActivityEvent(datetime=event_dt, activity=related_activity(), result=ActivityCompleted(result=result))
        elif event_type == 'ActivityTaskFailed':
            reason = attributes['reason']
            details = attributes['details']
            return ActivityEvent(datetime=event_dt, activity=related_activity(), result=ActivityFailed(reason=reason, details=details))
        elif event_type == 'ActivityTaskCanceled':
            details = attributes['details']
            return ActivityEvent(datetime=event_dt, activity=related_activity(), result=ActivityAborted(details=details))
        else:
            return None

    @classmethod
    def from_description(cls, description):
        execution_desc = description.get('workflowExecution', None) or description.get('execution', None)
        pid = execution_desc['workflowId']

        workflow = description.get('workflowType', {}).get('name', None)

        history = []
        event_descriptions = description.get('events', [])
        for event_description in event_descriptions:
            if event_description.get('workflowExecutionStartedEventAttributes', None):
                input = json.loads(event_description['workflowExecutionStartedEventAttributes']['input'])

            event = cls.event_from_description(event_description, related=event_descriptions)
            if event:
                history.append(event)

        return AmazonSWFProcess(id=pid, workflow=workflow, input=input, history=history)