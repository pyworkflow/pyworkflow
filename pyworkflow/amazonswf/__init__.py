from .. import Backend, ActivityTask, DecisionTask, Process
from ..task import (ScheduleActivity, CompleteProcess, TerminateProcess, ActivityCompleted, ActivityAborted, ActivityFailed)

import boto.swf
import json
import uuid
import time
from datetime import datetime, timedelta

class AmazonSWFProcess(Process):
    @classmethod
    def from_description(cls, description):
        execution_desc = description.get('workflowExecution', None) or description.get('execution', None)
        pid = execution_desc['workflowId']

        workflow = description.get('workflowType', {}).get('name', None)
        #workflow_version = description.get('workflowType', {}).get('version', None)

        events = description.get('events', None)
        if events:
            input = json.loads(events[0]['workflowExecutionStartedEventAttributes']['input'])
        else:
            input = None
        
        return AmazonSWFProcess(pid=pid, workflow=workflow, input=input)

class AmazonSWFDecisionTask(DecisionTask):
    def __init__(self, token, *args, **kwargs):
        super(AmazonSWFDecisionTask, self).__init__(*args, **kwargs)
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
        #activity_version = description['activityType']['version']
        input = json.loads(description.get('input'))
        process = AmazonSWFProcess.from_description(description)
        return AmazonSWFActivityTask(token, process, activity, input)

class AmazonSWFDecision(object):
    def __init__(self, decision):
        if isinstance(decision, ScheduleActivity):
            description = self.schedule_activity_description(decision)
        elif isinstance(decision, CompleteProcess):
            description = self.complete_process_description(decision)
        elif isinstance(decision, TerminateProcess):
            description = self.terminate_process_description(decision)

        self.description = description

    def schedule_activity_description(cls, decision):
        return {
            "decisionType": "ScheduleActivityTask",
            "scheduleActivityTaskDecisionAttributes": {
                "activityId": str(uuid.uuid4()),
                "activityType": {
                  "name": decision.activity,
                  "version": "1.0",
                },
                "control": None,
                #"heartbeatTimeout": SWF_TASK_HEARTBEAT_TIMEOUT if step.autocomplete else SWF_TASK_SCHEDULE_TO_CLOSE_TIMEOUT,
                "input": json.dumps(decision.input) if decision.input else None,
                #"scheduleToCloseTimeout": SWF_TASK_SCHEDULE_TO_CLOSE_TIMEOUT,
                #"scheduleToStartTimeout": SWF_TASK_SCHEDULE_TO_START_TIMEOUT,
                #"startToCloseTimeout": str(step.timeout) if step.timeout else SWF_TASK_START_TO_CLOSE_TIMEOUT,
                "taskList": {
                    "name": decision.category or "default"
                }
            }
        }

    def complete_process_description(self, decision):
        return {
            "decisionType": "CompleteWorkflowExecution",
            "completeWorkflowExecutionDecisionAttributes": {
                "result": json.dumps(decision.result)
            }
        }
        

class AmazonSWFBackend(Backend):
    
    @staticmethod
    def _get_region(name):
        return next((region for region in boto.swf.regions() if region.name == name), None )

    def __init__(self, access_key_id, secret_access_key, region='us-east-1', domain='default'):
        self.domain = domain
        self._swf = boto.swf.layer1.Layer1(access_key_id, secret_access_key, region=self._get_region(region))

    def register_workflow(self, name, timeout=Backend.DEFAULT_WORKFLOW_TIMEOUT):
        try:
            self._swf.describe_workflow_type(self.domain, name, "1.0")
        except:
            # Workflow type not registered yet
            self._swf.register_workflow_type(self.domain, name, version, 
                task_list='decisions', 
                default_child_policy='ABANDON',
                default_execution_start_to_close_timeout=str(timeout),
                default_task_start_to_close_timeout=str(timeout))

    def register_activity(self, name, category="default", timeout=Backend.DEFAULT_ACTIVITY_TIMEOUT, heartbeat_timeout=Backend.DEFAULT_ACTIVITY_HEARTBEAT_TIMEOUT):
        try:
            self._swf.describe_activity_type(self.domain, name, "1.0")
        except:
            self._swf.register_activity_type(self.domain, name, "1.0",
                task_list=category, 
                default_task_heartbeat_timeout=str(heartbeat_timeout),
                default_task_schedule_to_start_timeout=str(timeout), 
                default_task_schedule_to_close_timeout=str(timeout), 
                default_task_start_to_close_timeout=str(timeout))
    
    def start_process(self, process):
        self._swf.start_workflow_execution(
            self.domain, process.id, process.workflow, "1.0",
            input=json.dumps(process.input))
        
    def signal_process(self, process, signal, input=None):
        self._swf.signal_workflow_execution(
            self.domain, signal, process.id, 
            input=input)

    def cancel_process(self, process, details=None, reason=None):
        self._swf.terminate_workflow_execution(
            self.domain, process.id, 
            details=details,
            reason=reason)

    def complete_decision_task(self, task, decisions):
        if not isinstance(task, AmazonSWFDecisionTask):
            raise ValueError('Can only act on AmazonSWFDecisionTask')

        if not type(decisions) is list:
            decisions = [decisions]
        descriptions = [AmazonSWFDecision(d).description for d in decisions]

        self._swf.respond_decision_task_completed(task.token, 
            decisions=descriptions,
            execution_context=None)

    def complete_activity_task(self, task, result=None):
        if not isinstance(task, AmazonSWFActivityTask):
            raise ValueError('Can only act on AmazonSWFActivityTask')

        if isinstance(result, ActivityCompleted):
            self._swf.respond_activity_task_completed(task.token, result=json.dumps(result.result))
        elif isinstance(result, ActivityAborted):
            self._swf.respond_activity_task_canceled(task.token, details=result.details)
        elif isinstance(result, ActivityFailed):
            self._swf.respond_activity_task_failed(task.token, details=result.details, reason=result.error)
        else:
            raise ValueError('Expected result of type in [ActivityCompleted, ActivityAborted, ActivityFailed]')
    
    def processes(self, workflow=None, input=None, after_date=None):
        if not after_date:
            after_date = datetime.now() - timedelta(days=365)

        oldest_timestamp = time.mktime(after_date.timetuple())

        descriptions = self._swf.list_open_workflow_executions(self.domain, oldest_timestamp, workflow_name=workflow, tag=input.tag if input else None)
        return [AmazonSWFProcess.from_description(d) for d in descriptions['executionInfos']]

    def poll_activity_task(self, category="default"):
        description = self._swf.poll_for_activity_task(self.domain, category)
        return AmazonSWFActivityTask.from_description(description)

    def poll_decision_task(self):
        description = self._swf.poll_for_decision_task(self.domain, "decisions")
        return AmazonSWFDecisionTask.from_description(description)