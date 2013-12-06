import json
import uuid
import time
import boto.swf

from boto.exception import SWFResponseError
from datetime import datetime, timedelta
from itertools import imap

from .. import Backend
from ...exceptions import TimedOutException
from ...defaults import Defaults
from .process import AmazonSWFProcess, ActivityCompleted, ActivityFailed, ActivityAborted
from .task import decision_task_from_description, activity_task_from_description
from .decision import AmazonSWFDecision

        
class AmazonSWFBackend(Backend):
    
    @staticmethod
    def _get_region(name):
        return next((region for region in boto.swf.regions() if region.name == name), None )

    def __init__(self, access_key_id, secret_access_key, region='us-east-1', domain='default'):
        self.domain = domain
        self._swf = boto.swf.layer1.Layer1(access_key_id, secret_access_key, region=self._get_region(region))

    def _consume_until_exhaustion(self, request_fn):
        next_page_token = None
        while True:
            response = request_fn(next_page_token)
            yield response

            next_page_token = response.get('next_page_token', None)
            if not next_page_token:
                break
    
    def register_workflow(self, name, timeout=Defaults.WORKFLOW_TIMEOUT, decision_timeout=Defaults.DECISION_TIMEOUT):
        try:
            self._swf.describe_workflow_type(self.domain, name, "1.0")
        except:
            # Workflow type not registered yet
            self._swf.register_workflow_type(self.domain, name, "1.0", 
                task_list='decisions', 
                default_child_policy='ABANDON',
                default_execution_start_to_close_timeout=str(timeout),
                default_task_start_to_close_timeout=str(decision_timeout))

    def register_activity(self, name, category=Defaults.ACTIVITY_CATEGORY, 
        scheduled_timeout=Defaults.ACTIVITY_SCHEDULED_TIMEOUT, 
        execution_timeout=Defaults.ACTIVITY_EXECUTION_TIMEOUT, 
        heartbeat_timeout=Defaults.ACTIVITY_HEARTBEAT_TIMEOUT):

        try:
            self._swf.describe_activity_type(self.domain, name, "1.0")
        except:
            self._swf.register_activity_type(self.domain, name, "1.0",
                task_list=category, 
                default_task_heartbeat_timeout=str(heartbeat_timeout),
                default_task_schedule_to_start_timeout=str(scheduled_timeout), 
                default_task_schedule_to_close_timeout=str(scheduled_timeout+execution_timeout), 
                default_task_start_to_close_timeout=str(execution_timeout))
    
    def start_process(self, process):
        if process.tags and len(process.tags) > 5:
            raise ValueError('AmazonSWF supports a maximum of 5 tags per process')

        self._swf.start_workflow_execution(
            self.domain, process.id, process.workflow, "1.0",
            input=json.dumps(process.input),
            tag_list=process.tags)
        
    def signal_process(self, process, signal, data=None):
        self._swf.signal_workflow_execution(
            self.domain, signal, process.id, 
            input=json.dumps(data))

    def cancel_process(self, process, details=None, reason=None):
        self._swf.terminate_workflow_execution(
            self.domain, process.id, 
            details=details,
            reason=reason)

    def heartbeat_activity_task(self, task):
        self._swf.record_activity_task_heartbeat(task.context['token'])

    def complete_decision_task(self, task, decisions):
        if not type(decisions) is list:
            decisions = [decisions]
        descriptions = [AmazonSWFDecision(d).description for d in decisions]

        try:
            self._swf.respond_decision_task_completed(task.context['token'], 
                decisions=descriptions,
                execution_context=None)
        except SWFResponseError, e:
            if e.body.get('__type', None) == 'com.amazonaws.swf.base.model#UnknownResourceFault':
                raise TimedOutException()
            else:
                raise e

    def complete_activity_task(self, task, result=None):
        try:
            if isinstance(result, ActivityCompleted):
                self._swf.respond_activity_task_completed(task.context['token'], result=json.dumps(result.result))
            elif isinstance(result, ActivityAborted):
                self._swf.respond_activity_task_canceled(task.context['token'], details=result.details)
            elif isinstance(result, ActivityFailed):
                self._swf.respond_activity_task_failed(task.context['token'], details=result.details, reason=result.reason)
            else:
                raise ValueError('Expected result of type in [ActivityCompleted, ActivityAborted, ActivityFailed]')
        except SWFResponseError, e:
            if e.body.get('__type', None) == 'com.amazonaws.swf.base.model#UnknownResourceFault':
                raise TimedOutException()
            else:
                raise e
    
    def processes(self, workflow=None, tag=None):
        if workflow and tag:
            raise Exception('Amazon SWF does not support filtering on "workflow" and "tag" at the same time')

        # Max lifetime of workflow executions in SWF is 1 year
        after_date = datetime.now() - timedelta(days=365)
        oldest_timestamp = time.mktime(after_date.timetuple())

        def get_history(description):
            run_id = description['execution']['runId']
            workflow_id = description['execution']['workflowId']

            # exhaustively query execution history using next_page_token
            response_iter = self._consume_until_exhaustion(
                lambda token: self._swf.get_workflow_execution_history(self.domain, run_id, workflow_id, next_page_token=token),
            )

            return {'events': [ev for response in response_iter for ev in response['events']]}

        def mk_process(description):
            # get and fill in event history
            history = get_history(description)
            description.update(history)  
            return AmazonSWFProcess.from_description(description)                

        response_iter = self._consume_until_exhaustion(
            lambda token: self._swf.list_open_workflow_executions(self.domain, oldest_timestamp, workflow_name=workflow, tag=tag if input else None, next_page_token=token)
        )

        return imap(lambda d: mk_process(d), (d for response in response_iter for d in response['executionInfos']))

    def poll_activity_task(self, category="default", identity=None):
        description = self._swf.poll_for_activity_task(self.domain, category, identity=identity)
        return activity_task_from_description(description) if description else None

    def poll_decision_task(self, identity=None):
        description = self._swf.poll_for_decision_task(self.domain, "decisions", identity=identity)
        return decision_task_from_description(description) if description else None