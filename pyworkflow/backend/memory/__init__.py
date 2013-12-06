from itertools import ifilter
from collections import deque
from datetime import datetime, timedelta
from uuid import uuid4

from .. import Backend
from ...activity import *
from ...exceptions import TimedOutException
from ...event import *
from ...decision import *
from ...task import *
from ...signal import *
from ...defaults import Defaults

class MemoryBackend(Backend):
    '''
    Non-thread-safe in-memory workflow backend. Primarily for testing purposes.

    TODO: some basic locking on process queues for thread safety would be nice.
    '''

    def __init__(self):
        self.workflows = {}
        self.activities = {}

        self.running_processes = []
        self.running_activities = {}
        self.running_decisions = {}

        self.scheduled_decisions = deque([])
        self.scheduled_activities = deque([])

    def _managed_process(self, process):
        managed_process = next(ifilter(lambda p: p == process, self.running_processes), None)
        if not managed_process:
            raise Exception('Unknown process')
        return managed_process

    def _schedule_activity(self, process, activity, id, input):
        expiration = datetime.now() + timedelta(seconds=self.activities[activity]['scheduled_timeout'])
        execution = ActivityExecution(activity, id, input=input)
        self.scheduled_activities.append((execution, process, expiration))

    def _cancel_activity(self, id):
        to_cancel = filter(lambda a: a[0].id == decision.id, self.scheduled_activities)
        for a in to_cancel:
            self.scheduled_activities.remove(a)

        to_cancel = filter(lambda a: a[0].id == decision.id, self.running_activities)
        for a in to_cancel:
            self.running_activities.remove(a)

    def _schedule_decision(self, process):
        existing = filter(lambda a: a[0] == process, self.scheduled_decisions)
        if not len(existing):
            expiration = datetime.now() + timedelta(seconds=self.workflows[process.workflow]['decision_timeout'])
            self.scheduled_decisions.append((process, expiration))

    def _cancel_decision(self, process):
        to_cancel = filter(lambda a: a[0] == process, self.scheduled_decisions)
        for a in to_cancel:
            self.scheduled_decisions.remove(a)        

    def register_workflow(self, name, timeout=Defaults.WORKFLOW_TIMEOUT, decision_timeout=Defaults.DECISION_TIMEOUT):
        self.workflows[name] = {
            'timeout': timeout,
            'decision_timeout': decision_timeout
        }

    def register_activity(self, name, category=Defaults.ACTIVITY_CATEGORY, 
        scheduled_timeout=Defaults.ACTIVITY_SCHEDULED_TIMEOUT, 
        execution_timeout=Defaults.ACTIVITY_EXECUTION_TIMEOUT, 
        heartbeat_timeout=Defaults.ACTIVITY_HEARTBEAT_TIMEOUT):

        self.activities[name] = {
            'category': category,
            'scheduled_timeout': scheduled_timeout,
            'execution_timeout': execution_timeout,
            'heartbeat_timeout': heartbeat_timeout
        }

    def start_process(self, process):
        # register the process
        self.running_processes.append(process)
        # schedule a decision
        self._schedule_decision(process)
        
    def signal_process(self, process, signal, data=None):
        # find the process as we know it
        managed_process = self._managed_process(process)

        # append the signal event
        managed_process.history.append(SignalEvent(Signal(signal, data)))

        # schedule a decision (if needed)
        self._schedule_decision(managed_process)

    def cancel_process(self, process, details=None, reason=None):
        # find the process as we know it
        managed_process = self._managed_process(process)

        # append the cancelation event
        managed_process.history.append(DecisionEvent(CancelProcess(details=details, reason=reason)))

        # remove scheduled decision
        self._cancel_decision(managed_process)

        # remove process
        self.running_processes.remove(managed_process)

    def heartbeat_activity_task(self, task):
        self._time_out_activities()

        # find the process as we know it
        activity_execution = self.running_activities.get(task.context['run_id'])
        # replace with new heartbeat timeout
        self.running_activities.remove(activity)        
        activity[3] = datetime.now() + timedelta(seconds=self.activities[activity_execution.name]['heartbeat_timeout'])
        self.running_activities.append(activity)

    def complete_decision_task(self, task, decisions):
        self._time_out_decisions()
        
        if not type(decisions) is list:
            decisions = [decisions]

        # find the process as we know it
        decision = self.running_decisions.get(task.context['run_id'])
        if not decision:
            raise TimedOutException()
            
        (managed_process, expiration) = decision

        # append the decision events
        for decision in decisions:
            managed_process.history.append(DecisionEvent(decision))
            
            # schedule activity if needed
            if hasattr(decision, 'activity'):
                self._schedule_activity(managed_process, decision.activity, decision.id, decision.input)

            # cancel activity
            if isinstance(decision, CancelActivity):
                self._cancel_activity(decision.id)

            # complete process
            if isinstance(decision, CompleteProcess) or isinstance(decision, CancelProcess):
                self.running_processes.remove(managed_process)
                self._cancel_decision(managed_process)

    def complete_activity_task(self, task, result=None):
        self._time_out_activities()

        # find the process as we know it
        activity = self.running_activities.get(task.context['run_id'])
        if not activity:
            raise TimedOutException()

        (execution, managed_process, expiration, heartbeat_expiration) = activity

        # append the activity event
        managed_process.history.append(ActivityEvent(execution, result))

        # schedule a decision (if needed)
        self._schedule_decision(managed_process)

    def processes(self, workflow=None, tag=None):
        return ifilter(lambda p: (p.workflow == workflow or not workflow) and (tag in p.tags or not tag), self.running_processes)

    def _time_out_activities(self):
        # activities that are past expired scheduling date. they're in scheduled_activities
        for expired in filter(lambda a: a[2] < datetime.now(), self.scheduled_activities):
            self.scheduled_activities.remove(expired)
            self._schedule_decision(expired[1])

            expired[1].history.append(ActivityEvent(expired[0], ActivityTimedOut()))

        # activities that are past expired execution date. they're in running_activities
        for (i, expired) in filter(lambda (i,a): a[2] < datetime.now() or a[3] < datetime.now(), self.running_activities.items()):
            del self.running_activities[i]
            self._schedule_decision(expired[1])

            expired[1].history.append(ActivityEvent(expired[0], ActivityTimedOut()))

    def _time_out_decisions(self):
        # decisions that are past expired execution date. they're in running_decisions
        for (i,expired) in filter(lambda (i,a): a[1] < datetime.now(), self.running_decisions.items()):
            del self.running_decisions[i]
            self._schedule_decision(expired[0])

    def poll_activity_task(self, category="default", identity=None):
        # find queued activity tasks (that haven't timed out)
        try:
            while True:
                (activity_execution, process, expiration) = self.scheduled_activities.popleft()
                if expiration >= datetime.now():
                    break
        except:
            return None
        
        run_id = str(uuid4())
        expiration = datetime.now() + timedelta(seconds=self.activities[activity_execution.name]['execution_timeout'])
        heartbeat_expiration = datetime.now() + timedelta(seconds=self.activities[activity_execution.name]['heartbeat_timeout'])
        self.running_activities[run_id] = (activity_execution, process, expiration, heartbeat_expiration)

        return ActivityTask(activity_execution.name, input=activity_execution.input, context={'run_id': run_id}, process_id=process.id)

    def poll_decision_task(self, identity=None):
        # time-out expired activities
        self._time_out_activities()
        self._time_out_decisions()

        # find queued decision tasks (that haven't timed out)
        try:
            while True:
                (process, expiration) = self.scheduled_decisions.popleft()
                if expiration >= datetime.now():
                    break
        except:
            return None

        run_id = str(uuid4())
        expiration = datetime.now() + timedelta(seconds=self.workflows[process.workflow]['timeout'])
        self.running_decisions[run_id] = (process, expiration)
        
        return DecisionTask(process, context={'run_id': run_id})
        