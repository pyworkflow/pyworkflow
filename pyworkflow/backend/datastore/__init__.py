import pickle
import time

from itertools import ifilter, imap
from collections import deque
from datetime import datetime, timedelta
from uuid import uuid4

from datastore.core import Key, Query

from .. import Backend
from ...activity import *
from ...exceptions import UnknownActivityException, UnknownDecisionException, UnknownProcessException
from ...events import *
from ...decision import *
from ...process import Process
from ...task import *
from ...signal import *
from ...defaults import Defaults

class DatastoreBackend(Backend):
    '''
    Datastore backend. Not very efficient. Primarily for development purposes.
    '''

    KEY_RUNNING_PROCESSES = Key('/processes/running')
    KEY_RUNNING_ACTIVITIES = Key('/activities/running')
    KEY_RUNNING_DECISIONS = Key('/decisions/running')

    KEY_SCHEDULED_DECISIONS = Key('/decisions/scheduled')
    KEY_SCHEDULED_ACTIVITIES = Key('/activities/scheduled')

    def __init__(self, datastore):
        self.workflows = {}
        self.activities = {}

        self.datastore = datastore

    def _pickle_process(self, process):
        return {'pid': process['pid'], 'proc': pickle.dumps(process['proc'])}

    def _unpickle_process(self, process):
        return {'pid': process['pid'], 'proc': pickle.loads(process['proc'])}

    def _managed_process(self, process_or_pid):
        if isinstance(process_or_pid, basestring):
            match = lambda p: p['pid'] == process_or_pid
        else:
            match = lambda p: p['proc'].id == process_or_pid.id

        unpickled = map(lambda x: self._unpickle_process(x), self.datastore.query(Query(self.KEY_RUNNING_PROCESSES)))
        
        managed_process = filter(match, unpickled)
        if not managed_process:
            raise UnknownProcessException()
        
        return managed_process[0]

    def _save_managed_process(self, process):
        self.datastore.put(self.KEY_RUNNING_PROCESSES.child(process['pid']), self._pickle_process(process))

    def _schedule_activity(self, process, activity, id, input):
        expiration = datetime.now() + timedelta(seconds=self.activities[activity]['scheduled_timeout'])
        execution = ActivityExecution(activity, id, input=input)
        aid = str(uuid4())
        self.datastore.put(self.KEY_SCHEDULED_ACTIVITIES.child(aid), {'dt': time.time(), 'aid': aid, 'exec': pickle.dumps(execution), 'pid': process['pid'], 'exp': expiration})

    def _activity_by_id(self, id):
        activity = filter(lambda a: pickle.loads(a['exec']).id == id, self.datastore.query(Query(self.KEY_RUNNING_ACTIVITIES)))
        if not activity:
            activity = filter(lambda a: pickle.loads(a['exec']).id == id, self.datastore.query(Query(self.KEY_SCHEDULED_ACTIVITIES)))
        return (activity or [None])[0]        

    def _cancel_activity(self, id):
        to_cancel = filter(lambda a: pickle.loads(a['exec']).id == id, self.datastore.query(Query(self.KEY_SCHEDULED_ACTIVITIES)))
        for a in to_cancel:
            self.datastore.delete(self.KEY_SCHEDULED_ACTIVITIES.child(a['aid']))

        to_cancel = filter(lambda a: pickle.loads(a['exec']).id == id, self.datastore.query(Query(self.KEY_RUNNING_ACTIVITIES)))
        for a in to_cancel:
            self.datastore.delete(self.KEY_RUNNING_ACTIVITIES.child(a['run_id']))

    def _schedule_decision(self, process):
        existing = self.datastore.get(self.KEY_SCHEDULED_DECISIONS.child(process['pid']))
        if not existing:
            expiration = datetime.now() + timedelta(seconds=self.workflows[process['proc'].workflow]['decision_timeout'])
            self.datastore.put(self.KEY_SCHEDULED_DECISIONS.child(process['pid']), {'dt': time.time(), 'pid': process['pid'], 'exp': expiration})

    def _cancel_decision(self, process):
        self.datastore.delete(self.KEY_SCHEDULED_DECISIONS.child(process['pid']))

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
        managed_process = {'pid': process.id, 'proc': process}
        self._save_managed_process(managed_process)

        # schedule a decision
        self._schedule_decision(managed_process)
        
    def signal_process(self, process, signal, data=None):
        # find the process as we know it
        managed_process = self._managed_process(process)
        
        # append the signal event
        managed_process['proc'].history.append(SignalEvent(Signal(signal, data)))
        self._save_managed_process(managed_process)

        # schedule a decision (if needed)
        self._schedule_decision(managed_process)

    def cancel_process(self, process, details=None, reason=None):
        # find the process as we know it
        managed_process = self._managed_process(process)

        # append the cancelation event
        managed_process['proc'].history.append(DecisionEvent(CancelProcess(details=details, reason=reason)))
        self._save_managed_process(managed_process)

        # remove scheduled decision
        self._cancel_decision(managed_process)

        # process has already been removed on retrieve; don't re-save
        self.datastore.delete(self.KEY_RUNNING_PROCESSES.child(managed_process['pid']))


    def heartbeat_activity_task(self, task):
        self._time_out_activities()

        # find the process as we know it
        ae = self.datastore.get(self.KEY_RUNNING_ACTIVITIES.child(task.context['run_id']))
        (execution, pid, expiration, hb_expiration) = (pickle.loads(ae['exec']), ae['pid'], ae['exp'], ae['hb_exp'])

        # replace with new heartbeat timeout
        self.datastore.delete(self.KEY_RUNNING_ACTIVITIES.child(task.context['run_id']))
        expiration = datetime.now() + timedelta(seconds=self.activities[execution.activity]['heartbeat_timeout'])
        self.datastore.put(self.KEY_RUNNING_ACTIVITIES.child(task.context['run_id']), {'run_id': task.context['run_id'], 'exec': pickle.dumps(execution), 'pid': pid, 'exp': expiration, 'hb_exp': hb_expiration})

    def complete_decision_task(self, task, decisions):
        self._time_out_decisions()
        
        if not type(decisions) is list:
            decisions = [decisions]

        # find the process as we know it
        decision = self.datastore.get(self.KEY_RUNNING_DECISIONS.child(task.context['run_id']))
        if not decision:
            raise UnknownDecisionException()

        self.datastore.delete(self.KEY_RUNNING_DECISIONS.child(task.context['run_id']))
        (pid, expiration) = (decision['pid'], decision['exp'])
        managed_process = self._managed_process(pid)

        # append the decision events
        for decision in decisions:
            managed_process['proc'].history.append(DecisionEvent(decision))
            self._save_managed_process(managed_process)
            
            # schedule activity if needed
            if hasattr(decision, 'activity'):
                self._schedule_activity(managed_process, decision.activity, decision.id, decision.input)

            # cancel activity
            if isinstance(decision, CancelActivity):
                activity = self._activity_by_id(decision.id)
                self._cancel_activity(decision.id)
                managed_process['proc'].history.append(ActivityEvent(pickle.loads(activity['exec']), ActivityCanceled()))
                self._save_managed_process(managed_process)

            # complete process
            if isinstance(decision, CompleteProcess) or isinstance(decision, CancelProcess):
                for mp in filter(lambda mp: mp['pid'] == pid, self.datastore.query(Query(self.KEY_RUNNING_PROCESSES))):
                    self.datastore.delete(self.KEY_RUNNING_PROCESSES.child(mp['pid']))
                self._cancel_decision(managed_process)
                if managed_process['proc'].parent:
                    self._schedule_decision(self._managed_process(managed_process['proc'].parent))

            # start child process
            if isinstance(decision, StartChildProcess):
                process = Process(workflow=decision.process.workflow, id=decision.process.id, input=decision.process.input, tags=decision.process.tags, parent=task.process.id)
                managed_process = {'pid': process.id, 'proc': process}
                self._save_managed_process(managed_process)
                # schedule a decision
                self._schedule_decision(managed_process)
        

        # decision finished
        self.datastore.delete(self.KEY_RUNNING_DECISIONS.child(task.context['run_id']))

    def complete_activity_task(self, task, result=None):
        self._time_out_activities()

        # find the process as we know it
        activity = self.datastore.get(self.KEY_RUNNING_ACTIVITIES.child(task.context['run_id']))
        if not activity:
            raise UnknownActivityException()

        self.datastore.delete(self.KEY_RUNNING_ACTIVITIES.child(task.context['run_id']))
        (execution, pid, expiration, heartbeat_expiration) = (pickle.loads(activity['exec']), activity['pid'], activity['exp'], activity['hb_exp'])
        managed_process = self._managed_process(pid)

        # append the activity event
        managed_process['proc'].history.append(ActivityEvent(execution, result))
        self._save_managed_process(managed_process)

        # schedule a decision (if needed)
        self._schedule_decision(managed_process)

        # activity finished
        self.datastore.delete(self.KEY_RUNNING_ACTIVITIES.child(task.context['run_id']))

    def processes(self, workflow=None, tag=None):
        match = lambda p: (p['proc'].workflow == workflow or not workflow) and (tag in p['proc'].tags or not tag)
        return imap(lambda p: p['proc'], ifilter(match, imap(lambda x: self._unpickle_process(x), self.datastore.query(Query(self.KEY_RUNNING_PROCESSES)))))

    def _time_out_activities(self):
        # activities that are past expired scheduling date. they're in scheduled_activities
        for expired in filter(lambda a: a['exp'] < datetime.now(), self.datastore.query(Query(self.KEY_SCHEDULED_ACTIVITIES))):
            self.datastore.delete(self.KEY_SCHEDULED_ACTIVITIES.child(expired['aid']))

            managed_process = self._managed_process(expired['pid'])
            managed_process['proc'].history.append(ActivityEvent(pickle.loads(expired['exec']), ActivityTimedOut()))
            self._save_managed_process(managed_process)
            
            self._schedule_decision(managed_process)
            
        # activities that are past expired execution date. they're in running_activities
        for expired in filter(lambda a: a['exp'] < datetime.now() or a['hb_exp'] < datetime.now(), self.datastore.query(Query(self.KEY_RUNNING_ACTIVITIES))):
            self.datastore.delete(self.KEY_RUNNING_ACTIVITIES.child(expired['run_id']))

            managed_process = self._managed_process(expired['pid'])
            managed_process['proc'].history.append(ActivityEvent(pickle.loads(expired['exec']), ActivityTimedOut()))
            self._save_managed_process(managed_process)

            self._schedule_decision(managed_process)

    def _time_out_decisions(self):
        # decisions that are past expired execution date. they're in running_decisions
        for expired in filter(lambda a: a['exp'] < datetime.now(), self.datastore.query(Query(self.KEY_RUNNING_DECISIONS))):
            self.datastore.delete(self.KEY_RUNNING_DECISIONS.child(expired['run_id']))
            self._schedule_decision(self._managed_process(expired['pid']))

    def poll_activity_task(self, category="default", identity=None):
        # find queued activity tasks (that haven't timed out)
        self._time_out_activities()

        try:
            sa = sorted(self.datastore.query(Query(self.KEY_SCHEDULED_ACTIVITIES)), key=lambda sa: sa['dt'])
            if not sa:
                return None

            self.datastore.delete(self.KEY_SCHEDULED_ACTIVITIES.child(sa[0]['aid']))
            (pid, activity_execution, expiration) = (sa[0]['pid'], pickle.loads(sa[0]['exec']), sa[0]['exp'])
        except:
            return None
        
        run_id = str(uuid4())
        managed_process = self._managed_process(pid)
        expiration = datetime.now() + timedelta(seconds=self.activities[activity_execution.activity]['execution_timeout'])
        heartbeat_expiration = datetime.now() + timedelta(seconds=self.activities[activity_execution.activity]['heartbeat_timeout'])

        managed_process['proc'].history.append(ActivityStartedEvent(activity_execution))
        self._save_managed_process(managed_process)

        self.datastore.put(self.KEY_RUNNING_ACTIVITIES.child(run_id), {'run_id': run_id, 'exec': pickle.dumps(activity_execution), 'pid': pid, 'exp': expiration, 'hb_exp': heartbeat_expiration})
        return ActivityTask(activity_execution, process_id=pid, context={'run_id': run_id})

    def poll_decision_task(self, identity=None):
        # time-out expired activities
        self._time_out_activities()
        self._time_out_decisions()

        # find queued decision tasks (that haven't timed out)
        try:
            sa = sorted(self.datastore.query(Query(self.KEY_SCHEDULED_DECISIONS)), key=lambda sa: sa['dt'])
            if not sa:
                return None

            self.datastore.delete(self.KEY_SCHEDULED_DECISIONS.child(sa[0]['pid']))
            (pid, expiration) = (sa[0]['pid'], sa[0]['exp'])
        except:
            return None

        run_id = str(uuid4())
        process = self._managed_process(pid)['proc']
        expiration = datetime.now() + timedelta(seconds=self.workflows[process.workflow]['timeout'])
        self.datastore.put(self.KEY_RUNNING_DECISIONS.child(run_id), {'run_id': run_id, 'pid': pid, 'exp': expiration})
        
        return DecisionTask(process, context={'run_id': run_id})
        