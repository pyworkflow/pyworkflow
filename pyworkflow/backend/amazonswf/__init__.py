#from .. import Backend, ActivityTask, DecisionTask, Process
from .. import Backend

import boto.swf
import json
import uuid
import time
from datetime import datetime, timedelta

from .process import AmazonSWFProcess, ActivityCompleted, ActivityFailed, ActivityAborted
from .task import AmazonSWFDecisionTask, AmazonSWFActivityTask
from .decision import AmazonSWFDecision

import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)
        
class AmazonSWFBackend(Backend):
    
    @staticmethod
    def _get_region(name):
        return next((region for region in boto.swf.regions() if region.name == name), None )

    def __init__(self, access_key_id, secret_access_key, region='us-east-1', domain='default'):
        self.domain = domain
        self._swf = boto.swf.layer1.Layer1(access_key_id, secret_access_key, region=self._get_region(region))

    def _consume_until_exhaustion(self, request_fn, consume_fn):
        next_page_token = None
        while True:
            response = request_fn(next_page_token)
            for result in consume_fn(response):
                yield result
            next_page_token = response.get('next_page_token', None)
            if not next_page_token:
                break

    def register_workflow(self, name, timeout=Backend.DEFAULT_WORKFLOW_TIMEOUT):
        try:
            self._swf.describe_workflow_type(self.domain, name, "1.0")
        except:
            # Workflow type not registered yet
            self._swf.register_workflow_type(self.domain, name, "1.0", 
                task_list='decisions', 
                default_child_policy='ABANDON',
                default_execution_start_to_close_timeout=str(timeout),
                default_task_start_to_close_timeout=str(Backend.DEFAULT_DECISION_TIMEOUT))

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
            self._swf.respond_activity_task_failed(task.token, details=result.details, reason=result.reason)
        else:
            raise ValueError('Expected result of type in [ActivityCompleted, ActivityAborted, ActivityFailed]')
    
    def processes(self, workflow=None, input=None, after_date=None):
        if not after_date:
            after_date = datetime.now() - timedelta(days=365)

        oldest_timestamp = time.mktime(after_date.timetuple())

        def get_history(description):
            run_id = description['execution']['runId']
            workflow_id = description['execution']['workflowId']

            def consume(response):
                for event in response['events']:
                    yield event
            
            event_gen = self._consume_until_exhaustion(
                request_fn = lambda token: self._swf.get_workflow_execution_history(self.domain, run_id, workflow_id, next_page_token=token),
                consume_fn = consume
            )

            return {'events': list(event_gen)}

        def process_gen():
            def consume(response):
                for description in response['executionInfos']:
                    history = get_history(description)
                    description.update(history)  
                    yield AmazonSWFProcess.from_description(description)

            return self._consume_until_exhaustion(
                request_fn = lambda token: self._swf.list_open_workflow_executions(self.domain, oldest_timestamp, workflow_name=workflow, tag=input.tag if input else None, next_page_token=token),
                consume_fn = consume
            )

        return process_gen()

    def poll_activity_task(self, category="default"):
        description = self._swf.poll_for_activity_task(self.domain, category)
        return AmazonSWFActivityTask.from_description(description) if description else None

    def poll_decision_task(self):
        description = self._swf.poll_for_decision_task(self.domain, "decisions")
        return AmazonSWFDecisionTask.from_description(description) if description else None