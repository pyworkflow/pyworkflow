import logging
import unittest
import mock

from freezegun import freeze_time
from copy import deepcopy
from time import sleep

from datetime import datetime, timedelta
from ..exceptions import UnknownActivityException
from ..process import Process, ProcessCompleted
from ..activity import ActivityExecution, ActivityCompleted, ActivityFailed, ActivityCanceled
from ..decision import ScheduleActivity, CompleteProcess, CancelProcess, CancelActivity, StartChildProcess, Timer
from ..events import ProcessStartedEvent, DecisionStartedEvent, DecisionEvent, ActivityEvent, ActivityStartedEvent, SignalEvent, ChildProcessEvent, TimerEvent
from ..signal import Signal
from ..task import ActivityTask

from ..managed import Activity, ActivityMonitor, Workflow, RuleSetWorkflow, Manager
from ..managed.worker import ActivityWorker, DecisionWorker, WorkerThread
from ..managed.workflow import rules

logging.getLogger('workflow').setLevel('DEBUG')

pending_shipments = []

timer_delay = 1

class DelayedExecution:
    def __init__(self, delay, use_sleep):
        self.delay = delay if hasattr(delay, 'seconds') else timedelta(seconds=delay)
        self.use_sleep = use_sleep
        self.freezer = None

    def __enter__(self):
        if self.use_sleep:
            sleep(self.delay.total_seconds())
        else:
            self.freezer = freeze_time(datetime.now() + self.delay)
            self.freezer.start()

    def __exit__(self, *args):
        if self.freezer:
            self.freezer.stop()

def delay(delay, use_sleep=False):
    return DelayedExecution(delay, use_sleep)

class MultiplicationActivity(Activity):
    category = 'computation'

    def execute(self):
        self.heartbeat()

        if not type(self.input) is list or len(self.input) != 2:
            raise ValueError('invalid input; expected list of length 2')
        
        return self.input[0] * self.input[1]

class FooWorkflow(Workflow):
    scheduled_timeout = 2
    execution_timeout = 5
    heartbeat_timeout = 5

    activities = [MultiplicationActivity]

    def decide(self, process):
        if len(process.history) <= 2: # started
            return ScheduleActivity(MultiplicationActivity, input=process.input)
        else:
            return CompleteProcess()

class TimerTestWorkflow(Workflow):
    def decide(self, process):
        if len(process.history) <= 2: # started
            return Timer(timer_delay, {'foo': 'bar'})
        else:
            return CompleteProcess()

class PaymentProcessingActivity(Activity):
    def execute(self):
        return True

class ShipmentActivity(Activity):
    auto_complete = False

    def execute(self):
        pending_shipments.append(self.task)
        return True

class CancelOrderActivity(Activity):
    def execute(self):
        return True


class OrderWorkflow(RuleSetWorkflow):
    activities = [PaymentProcessingActivity, ShipmentActivity, CancelOrderActivity]

    @rules.process_started
    def initiate(self, event, process):
        return ScheduleActivity(PaymentProcessingActivity)

    @rules.completed_activity(activity='PaymentProcessing')
    def on_completed_payment(self, event, process):
        return [ScheduleActivity(ShipmentActivity, input=item) for item in process.input['items']]

    @rules.completed_activity(activity='Shipment')
    def on_completed_shipment(self, event, process):
        if process.unfinished_activities():
            return []

        def is_interrupted_event(event):
            return isinstance(event, ActivityEvent) and (isinstance(event.result, ActivityFailed) or isinstance(event.result, ActivityCanceled))

        if not filter(lambda ev: ev.activity_execution.activity == 'Shipment', filter(is_interrupted_event, process.unseen_events())):
            return CompleteProcess()

    @rules.completed_activity(activity='CancelOrder')
    def on_completed_cancel(self, event, process):
        return CancelProcess()

    @rules.interrupted_activity(activity='PaymentProcessing')
    def on_failed_payment(self, event, process):
        return CancelProcess('payment_aborted')

    @rules.interrupted_activity(activity='Shipment')
    def on_failed_shipment(self, event, process):
        decisions = []
        for activity_execution in process.unfinished_activities():
            decisions.append(CancelActivity(activity_execution.id))
        decisions.append(ScheduleActivity(CancelOrderActivity, input=process.input))
        return decisions

    @rules.signal(name='extra_shipment')
    def on_extra_shipment(self, event, process):
        return ScheduleActivity(ShipmentActivity, input=event.signal.data)


class TimeoutActivity(Activity):
    scheduled_timeout = 1
    execution_timeout = 2
    heartbeat_timeout = 1

    def execute(self):
        duration = self.input['duration']
        heartbeat = self.input.get('heartbeat', False)
        use_sleep = self.input.get('sleep', False)

        # input[0] for regular sleep
        # input[1] for sleep with 10 heartbeats
        if heartbeat:
            for i in range(0, 10):
                if not use_sleep:
                    with delay((float(duration)/10.0)*i):
                        self.heartbeat()
                else:
                    sleep(float(duration)/10.0)
                    self.heartbeat()
        else:
            if use_sleep:
                sleep(duration)
            
        return True

class TimeoutWorkflow(Workflow):
    activities = [TimeoutActivity]

    def decide(self, process):
        use_sleep = process.input.get('sleep', False)

        if len(process.history) == 2: # process start + decision start
            # let it time out on schedule
            return ScheduleActivity(TimeoutActivity, input={'duration':0,'sleep':use_sleep}, id=1)
        elif len(process.history) < 6: # process start + decision start + decision + activity start + timeout + decision start
            # let it time out on heartbeat
            return ScheduleActivity(TimeoutActivity, input={'duration':2,'sleep':use_sleep}, id=2)
        elif len(process.history) < 10: # process start + decision start + decision + activity start + timeout + decision start + decision + activity start + timeout + decision start
            # let it time out on execution
            return ScheduleActivity(TimeoutActivity, input={'duration':2, 'heartbeat':True,'sleep':use_sleep}, id=3)
        else:
            return CompleteProcess()

class WorkflowBasicTestCase(unittest.TestCase):

    def test_basic(self):
        ''' Test basic functionality outside of a backend '''

        # start a new FooWorkflow process
        workflow = FooWorkflow()
        process = Process(workflow=workflow, input=[2,3])
        assert len(process.history) == 1
        assert process.history[0].type == 'process_started'

        # take a decision
        process.history.append(DecisionStartedEvent())
        decision = workflow.decide(process)
        assert isinstance(decision, ScheduleActivity)
        assert decision.input == [2,3]
        assert decision.activity == 'Multiplication'
        process.history.append(DecisionEvent(decision))
        assert (datetime.now() - process.history[0].datetime).seconds == 0

        # execute the activity
        heartbeat = mock.Mock()
        monitor = ActivityMonitor(heartbeat_fn=heartbeat)
        activity_execution = ActivityTask(ActivityExecution('Multiplication',123,input=decision.input))
        result = MultiplicationActivity(activity_execution, monitor).execute()
        assert heartbeat.call_count == 1
        assert result == 6
        process.history.append(ActivityEvent(activity_execution, ActivityCompleted(result)))
        assert (datetime.now() - process.history[1].datetime).seconds == 0

        # take a decision
        process.history.append(DecisionStartedEvent())
        decision = workflow.decide(process)
        assert isinstance(decision, CompleteProcess)
        process.history.append(DecisionEvent(decision))

    def test_process(self):
        process = Process(id='p1', workflow='test', input=2, tags=[], history=[
            SignalEvent(signal=Signal('signal1', {'test': 123})),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('act1', id='1', input=2)),
            SignalEvent(signal=Signal('signal2', {'test': 123})),
            DecisionStartedEvent()
        ])

        assert process.unseen_events() == [
            DecisionEvent(decision=ScheduleActivity('act1', id='1', input=2)),
            SignalEvent(signal=Signal('signal2', {'test': 123}))
        ]

        process.history.append(DecisionEvent(decision=StartChildProcess(Process(id='p2', workflow='testsub', input=1))))
        assert process.unseen_events() == []

        unfinished = process.unfinished_activities()
        assert unfinished == [ActivityExecution('act1', '1', 2)]


class WorkflowBackendTestCase(unittest.TestCase):

    is_external = False

    def construct_backend(self):
        raise NotImplementedError()

    def subtest_timeouts(self):
        backend = self.construct_backend()
        manager = Manager(backend, workflows=[TimeoutWorkflow])

        # Start a new TimeoutWorkflow process
        process = Process(workflow=TimeoutWorkflow, input={'sleep': self.is_external})
        manager.start_process(process)

        # Decide initial activity
        task = manager.next_decision()
        assert task
        workflow = manager.workflow_for_task(task)
        decision = workflow.decide(task.process)
        assert decision == ScheduleActivity(TimeoutActivity, input={'duration':0,'sleep':self.is_external}, id=1)
        manager.complete_task(task, decision)

        # Let the schedule time-out hit
        with delay(1, self.is_external):
            # The task should be passed back to the decider
            task = manager.next_decision()
            assert task

        workflow = manager.workflow_for_task(task)
        decision = workflow.decide(task.process)
        assert decision == ScheduleActivity(TimeoutActivity, input={'duration':2,'sleep':self.is_external}, id=2)
        manager.complete_task(task, decision)

        # This time, execute the activity and time out before heartbeat
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        with delay(1, self.is_external): # heartbeat timeout == 1
            try:
                manager.complete_task(task, ActivityCompleted(result=True))
                assert False, "should have timed out and not allowed completion"
            except UnknownActivityException, e:
                pass

        # The task should be passed back to the decider
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decision = workflow.decide(task.process)
        assert decision == ScheduleActivity(TimeoutActivity, input={'duration':2,'heartbeat':True,'sleep':self.is_external}, id=3)
        manager.complete_task(task, decision)
        
        # This time, execute the activity and time out on execution
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        result = activity.execute()
        with delay(2, self.is_external): # execution timeout == 2
            try:
                manager.complete_task(task, ActivityCompleted(result=result))
                assert False, "should have timed out and not allowed completion"
            except UnknownActivityException, e:
                pass

    def subtest_basic(self):
        ''' Tests the basic backend functionality (no Workflow / Activity objects involved) '''

        backend = self.construct_backend()

        # Register workflow and activity types
        backend.register_workflow('test')
        backend.register_activity('double')

        # Start a new workflow process
        backend.start_process(Process(workflow='test', input=2, tags=["process-1234", "foo"]))
        backend.start_process(Process(workflow='test', input=3, tags=["process-5678"]))

        # Verify we can read it back by tags
        processes = list(backend.processes(tag="foo"))
        assert len(processes) == 1
        pid1 = processes[0].id
        assert processes == [Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"])]
        
        processes = list(backend.processes(tag="process-5678"))
        assert len(processes) == 1
        pid2 = processes[0].id
        assert processes == [Process(id=pid2, workflow='test', input=3, tags=["process-5678"])]
        

        # Verify we can read the process back in a list
        assert hasattr(backend.processes(), '__iter__')
        processes = sorted(list(backend.processes()), key=lambda p: p.input)
        assert len(processes) == 2        

        assert processes[0] == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"])
        assert processes[1] == Process(id=pid2, workflow='test', input=3, tags=["process-5678"])

        processes = sorted(list(backend.processes(workflow="test")), key=lambda p: p.input)
        assert processes[0] == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"])
        assert processes[1] == Process(id=pid2, workflow='test', input=3, tags=["process-5678"])

        # Terminate the second process
        processes = list(backend.processes(tag="process-5678"))
        backend.cancel_process(processes[0].id)
        processes = list(backend.processes())
        assert processes[0] == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"])

        # Verify we get the first decision task back
        task = backend.poll_decision_task()
        assert task.process.id == pid1
        #assert task.process == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"])
        
        # Execute the decision task (schedule activity)
        activity_id = '5678'
        backend.complete_decision_task(task, ScheduleActivity('double', id=activity_id, input=task.process.input))
        date_scheduled = datetime.now()

        # Verify we can read the process back
        processes = list(backend.processes())
        expected = Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"], history=[
            ProcessStartedEvent(),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled)
        ])
        assert len(processes) == 1
        assert processes[0] == expected
        assert backend.process_by_id(pid1) == expected


        # Send a signal
        backend.signal_process(processes[0].id, 'some_signal', data={'test': 123})

        # Verify the signal is in the history
        processes = list(backend.processes())
        assert len(processes) == 1
        assert processes[0] == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"], history=[
            ProcessStartedEvent(),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123}))
            ])

        # Verify we get the activity task back now
        task = backend.poll_activity_task()
        assert task.activity_execution.activity == 'double'
        assert task.activity_execution.input == 2

        # Simulate activity task failure
        backend.complete_activity_task(task, ActivityFailed(reason='simulated error', details='unknown'))
        date_failed = datetime.now()

        # Verify we can read the process back
        processes = list(backend.processes())
        assert len(processes) == 1
        assert processes[0] == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"], history=[
            ProcessStartedEvent(),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed)
            ])

        # Re-schedule the task
        task = backend.poll_decision_task()
        backend.complete_decision_task(task, ScheduleActivity('double', id=activity_id, input=task.process.input))
        date_scheduled2 = datetime.now()

        # Simulate activity task abortion
        task = backend.poll_activity_task()
        backend.complete_activity_task(task, ActivityCanceled(details='test'))
        date_aborted = datetime.now()

        # Verify we can read the process back
        processes = list(backend.processes())
        assert len(processes) == 1
        assert processes[0] == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"], history=[
            ProcessStartedEvent(),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled2),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCanceled(details='test'), datetime=date_aborted)
            ])

        # Re-schedule the task
        task = backend.poll_decision_task()
        backend.complete_decision_task(task, ScheduleActivity('double', id=activity_id, input=task.process.input))
        date_scheduled3 = datetime.now()
        
        # Simulate activity task completion (perform input*2)
        task = backend.poll_activity_task()
        backend.complete_activity_task(task, ActivityCompleted(result=task.activity_execution.input * 2))
        date_completed = datetime.now()
        
        # Verify we can read the process back
        processes = list(backend.processes())
        assert len(processes) == 1
        assert processes[0] == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"], history=[
            ProcessStartedEvent(),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled2),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCanceled(details='test'), datetime=date_aborted),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled3),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCompleted(result=4), datetime=date_completed)
            ])
        
        # Verify we get a decision task
        task = backend.poll_decision_task()      
        assert task.process.workflow == 'test'
        # Verify the history is there in the task as well
        assert task.process == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"], history=[
            ProcessStartedEvent(),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled2),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCanceled(details='test'), datetime=date_aborted),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled3),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCompleted(result=4), datetime=date_completed),
            DecisionStartedEvent()
            ])

        # Start child process
        child_process = Process(workflow='test', input=[3,4], tags=[u'test-child'])
        backend.complete_decision_task(task, StartChildProcess(child_process))

        # Verify the start child process is in the history
        processes = list(backend.processes(tag='foo'))
        assert processes[0] == Process(id=pid1, workflow='test', input=2, tags=["process-1234", "foo"], history=[
            ProcessStartedEvent(),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled2),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCanceled(details='test'), datetime=date_aborted),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled3),
            ActivityStartedEvent(ActivityExecution('double', activity_id, 2)),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCompleted(result=4), datetime=date_completed),
            DecisionStartedEvent(),
            DecisionEvent(decision=StartChildProcess(child_process))
            ])

        parent_id = task.process.id

        task = backend.poll_decision_task()
        assert task.process.workflow == 'test'
        assert task.process.parent == parent_id
        assert task.process.id is not None

        child_id = task.process.id

        # Complete the child process
        backend.complete_decision_task(task, CompleteProcess(result=50))

        if self.is_external:
            sleep(.5)

        # Complete the parent process
        task = backend.poll_decision_task()
        assert task.process.history[-2] == ChildProcessEvent(process_id=child_id, result=ProcessCompleted(result=50), workflow='test', tags=[u'test-child'])
        backend.complete_decision_task(task, CompleteProcess())
        
        # Verify there are now no more processes
        processes = list(backend.processes())
        assert processes == []

        # Register an activity in a different category
        backend.register_workflow('test2', category='heavy_decisions')
        backend.register_activity('triple', category='heavy')

        # Start a new workflow process
        backend.start_process(Process(workflow='test2', input=2, tags=["foo"]))

        # we shouldn't see decisions on the regular queue
        if not self.is_external:
            # this could cause a time-out for external backends
            task = backend.poll_decision_task()
            assert task is None

        # But we should see it on the heavy queue
        task = backend.poll_decision_task('heavy_decisions')
        assert task is not None
        activity_id = '999'
        backend.complete_decision_task(task, ScheduleActivity('triple', id=activity_id, input=task.process.input))
        date_scheduled = datetime.now()

        # Verify we don't get the activity task back from the default queue
        if not self.is_external:
            # this could cause a time-out for external backends
            task = backend.poll_activity_task()
            assert task is None

        # But we do get it from the heavy queue
        task = backend.poll_activity_task(category='heavy')
        assert task.activity_execution.activity == 'triple'
        assert task.activity_execution.input == 2
        backend.complete_activity_task(task, ActivityCanceled('notreally'))

        # Schedule a normal activity, but put it in the heavy queue
        task = backend.poll_decision_task('heavy_decisions')
        activity_id = '999'
        backend.complete_decision_task(task, ScheduleActivity('double', id=activity_id, input=task.process.input, category='heavy'))
        date_scheduled = datetime.now()

        # Verify we don't get the activity task back from the default queue
        if not self.is_external:
            # this could cause a time-out for external backends
            task = backend.poll_activity_task()
            assert task is None

        # Verify we can read the task from the heavy queue
        task = backend.poll_activity_task(category='heavy')
        assert task.activity_execution.activity == 'double'
        assert task.activity_execution.input == 2
        

    def subtest_managed(self):
        backend = self.construct_backend()
        
        # Create a manager and register the workflow
        manager = Manager(backend, workflows=[FooWorkflow])

        # Start a new FooWorkflow process
        process = Process(workflow=FooWorkflow, input=[2,3])
        manager.start_process(process)

        # Decide initial activity
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        assert workflow == FooWorkflow()
        assert task.process.workflow == 'Foo'
        assert task.process.input == [2,3]        

        decision = workflow.decide(task.process)
        manager.complete_task(task, decision)

        # Some properties to compare later
        activity_id = decision.id
        date_scheduled = datetime.now()
        
        # Run the activity
        task = manager.next_activity(category='computation')
        activity = manager.activity_for_task(task)
        assert activity == MultiplicationActivity(task)
        assert task.activity_execution.activity == 'Multiplication'
        assert task.activity_execution.input == [2,3]
        result = activity.execute()
        assert result == 6
        manager.complete_task(task, ActivityCompleted(result=result))
        date_completed = datetime.now()

        pid = task.process_id

        # Decide completion
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        assert task.process.workflow == 'Foo'
        expected = Process(id=pid, workflow='Foo', input=[2,3], history=[
            ProcessStartedEvent(),
            DecisionStartedEvent(),
            DecisionEvent(decision=ScheduleActivity('Multiplication', id=activity_id, input=[2,3]), datetime=date_scheduled),
            ActivityStartedEvent(ActivityExecution('Multiplication', activity_id, [2,3])),
            ActivityEvent(ActivityExecution('Multiplication', activity_id, [2,3]), result=ActivityCompleted(result=6), datetime=date_completed),
            DecisionStartedEvent()
        ])
        assert task.process == expected

        decision = workflow.decide(task.process)
        manager.complete_task(task, decision)

    def subtest_order(self):
        backend = self.construct_backend()
        
        # Create a manager and register the workflow
        manager = Manager(backend, workflows=[OrderWorkflow])

        worker = ActivityWorker(manager)

        #
        # Order that will fail in payment
        #
        # Start order workflow
        process = Process(workflow=OrderWorkflow, input={'items': [100, 200]}, tags=["order-1", "foo", "bar"])
        manager.start_process(process)

        read_back = list(manager.processes(workflow=OrderWorkflow))
        assert read_back == [process.copy_with_id(read_back[0].id)]
        
        read_back = list(manager.processes(tag="order-1"))
        assert read_back == [process.copy_with_id(read_back[0].id)]
        
        # Decide: -> payment processing
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Activity: abort
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityCanceled())
        
        # Decide: -> terminate
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Verify process terminated
        assert list(manager.processes()) == []

        #
        # Order that will complete fully
        #
        # Start order workflow
        process = Process(workflow=OrderWorkflow, input={'items': [100, 200]})
        manager.start_process(process)
        
        # Decide: -> payment processing
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Activity: complete
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityCompleted())
        
        # Decide: -> shipment x2
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Activity: complete one, use worker
        #task = manager.next_activity()
        #activity = manager.activity_for_task(task)
        worker.step()
        assert len(pending_shipments) == 1
        task = pending_shipments.pop()
        manager.complete_task(task, ActivityCompleted())
        
        # Decide: -> nothing
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        assert decisions == []
        manager.complete_task(task, decisions)

        # Activity: signal other
        worker.step()
        assert len(pending_shipments) == 1
        task2 = pending_shipments.pop()        
        manager.signal_process(task.process, Signal('extra_shipment', data=300))

        # Decide: -> extra shipment
        task = manager.next_decision()
        decisions = workflow.decide(task.process)
        assert len(decisions) == 1
        assert isinstance(decisions[0], ScheduleActivity)
        assert decisions[0].activity == 'Shipment'
        manager.complete_task(task, decisions)

        # Activity: complete both
        worker.step()
        assert len(pending_shipments) == 1
        task = pending_shipments.pop()        
        manager.complete_task(task, ActivityCompleted())
        manager.complete_task(task2, ActivityCompleted())
        
        # Decide: -> complete
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Verify completion
        assert decisions == [CompleteProcess()]
        assert list(manager.processes()) == []


        #
        # Order that will fail in shipment
        #
        # Start order workflow
        process = Process(workflow=OrderWorkflow, input={'items': [100, 200]})
        manager.start_process(process)
        
        # Decide: -> payment processing
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Activity: complete
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityCompleted())
        
        # Decide: -> shipment x2
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Activity: complete one, fail other
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityCompleted())
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityFailed())
        
        # Decide: -> cancel
        task = manager.next_decision()
        decisions = workflow.decide(task.process)
        assert len(decisions) == 1
        assert isinstance(decisions[0], ScheduleActivity)
        assert decisions[0].activity == 'CancelOrder'
        manager.complete_task(task, decisions)

        # Activity: complete
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityCompleted())
        
        # Decide: -> terminate
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Verify termination
        assert decisions == [CancelProcess()]
        assert list(manager.processes()) == []

    def subtest_timer(self):
        backend = self.construct_backend()
        manager = Manager(backend, workflows=[TimerTestWorkflow])

        process = Process(workflow=TimerTestWorkflow)
        manager.start_process(process)

        processes = list(backend.processes())
        assert len(processes) == 1
        pid = processes[0].id

        # Decide: -> timer
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decision = workflow.decide(task.process)
        date_scheduled = datetime.now()
        manager.complete_task(task, decision)
        self.assertEquals(decision, Timer(timer_delay, {'foo': 'bar'}))

        # no use checking for absence of tasks here, some backends are long-polling
        with delay(timer_delay, self.is_external):
            # Activity: abort
            task = manager.next_decision()
            assert task.process == Process(id=pid, workflow='TimerTest', input=None, tags=[], history=[
                ProcessStartedEvent(),
                DecisionStartedEvent(),
                DecisionEvent(decision=Timer(timer_delay, {'foo': 'bar'}), datetime=date_scheduled),
                TimerEvent(timer=Timer(timer_delay, {'foo': 'bar'})),
                DecisionStartedEvent()
                ])

        workflow = manager.workflow_for_task(task)
        decision = workflow.decide(task.process)
        manager.complete_task(task, decision)
        
        processes = list(backend.processes())
        assert len(processes) == 0

    def subtest_threads(self):
        '''
        Tests merely completion of a workflow handed to threads, not functional correctness.
        '''

        manager = Manager(self.construct_backend(), workflows=[FooWorkflow])

        # Start a decider thread (use new backend not to share connection)
        decider_mgr = manager.copy_with_backend(self.construct_backend())
        # make sure backend is fully initialized
        assert len(list(decider_mgr.processes())) == 0
        decider = WorkerThread(DecisionWorker(decider_mgr))
        decider.start()

        # Start an activity worker thread
        worker_mgr = manager.copy_with_backend(self.construct_backend())
        # make sure backend is fully initialized
        assert len(list(worker_mgr.processes())) == 0
        worker = WorkerThread(ActivityWorker(worker_mgr, category='computation'))
        worker.start()

        # Start a new FooWorkflow process
        process = Process(workflow=FooWorkflow, input=[2,3])
        manager.start_process(process)

        assert len(list(manager.processes())) == 1

        # We expect this to take no more than 4 seconds
        for _ in range(0,40):
            if len(list(manager.processes())) == 0:
                break
            sleep(.1) # have to use sleep because of different runtimes

        decider.join(1)
        worker.join(1)
        assert len(list(manager.processes())) == 0