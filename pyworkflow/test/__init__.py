import logging
import unittest
import mock
from time import sleep

from datetime import datetime
from ..exceptions import TimedOutException
from ..workflow import Workflow, DefaultWorkflow
from ..process import Process
from ..activity import Activity, ActivityExecution, ActivityMonitor, ActivityCompleted, ActivityFailed, ActivityAborted
from ..decision import ScheduleActivity, CompleteProcess, CancelProcess
from ..event import DecisionEvent, ActivityEvent, SignalEvent
from ..signal import Signal
from ..manager import Manager
from ..worker import ActivityWorker, DecisionWorker, WorkerThread

logging.getLogger('workflow').setLevel('DEBUG')

class MultiplicationActivity(Activity):
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
        if len(process.history) == 0:
            return ScheduleActivity(MultiplicationActivity, input=process.input)
        else:
            return CompleteProcess()

class PaymentProcessingActivity(Activity):
    def execute(self):
        return True
class ShipmentActivity(Activity):
    def execute(self):
        return True
class CancelOrderActivity(Activity):
    def execute(self):
        return True

class OrderWorkflow(DefaultWorkflow):
    activities = [PaymentProcessingActivity, ShipmentActivity, CancelOrderActivity]

    def initiate(self, process):
        return ScheduleActivity(PaymentProcessingActivity)

    def respond_to_completed_activity(self, process, activity, result):
        if activity.name == 'PaymentProcessing':
            return [ScheduleActivity(ShipmentActivity, input=item) for item in process.input['items']]

        if activity.name == 'Shipment':
            if process.unfinished_activities():
                return []

            def is_interrupted_event(event):
                return isinstance(event, ActivityEvent) and (isinstance(event.result, ActivityFailed) or isinstance(event.result, ActivityAborted))

            if not filter(lambda ev: ev.activity.name == 'Shipment', filter(is_interrupted_event, process.unseen_events())):
                return CompleteProcess()

        if activity.name == 'CancelOrder':
            return CancelProcess()

    def respond_to_interrupted_activity(self, process, activity, result):
        if activity.name == 'PaymentProcessing':
            return CancelProcess('payment_aborted')

        if activity.name == 'Shipment':
            decisions = []
            for activity in process.unfinished_activities():
                decisions.append(CancelActivity(activity.id))
            decisions.append(ScheduleActivity(CancelOrderActivity, input=process.input))
            return decisions

    def respond_to_signal(self, process, signal):
        if signal.name == 'extra_shipment':
            return ScheduleActivity(ShipmentActivity, input=signal.data)


class TimeoutActivity(Activity):
    scheduled_timeout = 1
    execution_timeout = 2
    heartbeat_timeout = 1

    def execute(self):
        if self.input[0]:
            sleep(self.input[0])
        else:
            for _ in range(0, 10):
                sleep(float(self.input[1])/10.0)
                self.heartbeat()
        return True

class TimeoutWorkflow(Workflow):
    activities = [TimeoutActivity]

    def decide(self, process):
        if len(process.history) == 0:
            # let it time out on schedule
            return ScheduleActivity(TimeoutActivity, input=[0,0], id=1)
        elif len(process.history) < 3:
            # let it time out on heartbeat
            return ScheduleActivity(TimeoutActivity, input=[2,0], id=2)
        elif len(process.history) < 6:
            # let it time out on execution
            return ScheduleActivity(TimeoutActivity, input=[0,5], id=3)
        else:
            return CompleteProcess()

class WorkflowBasicTestCase(unittest.TestCase):

    def test_basic(self):
        ''' Test basic functionality outside of a backend '''

        # start a new FooWorkflow process
        workflow = FooWorkflow()
        process = Process(workflow=workflow, input=[2,3])
        assert process.history == []

        # take a decision
        decision = workflow.decide(process)
        assert isinstance(decision, ScheduleActivity)
        assert decision.input == [2,3]
        assert decision.activity == 'Multiplication'
        process.history.append(DecisionEvent(decision))
        assert (datetime.now() - process.history[0].datetime).seconds == 0

        # execute the activity
        heartbeat = mock.Mock()
        monitor = ActivityMonitor(heartbeat_fn=heartbeat)
        result = MultiplicationActivity(decision.input, monitor).execute()
        assert heartbeat.call_count == 1
        assert result == 6
        process.history.append(ActivityEvent(ActivityExecution('Multiplication', 123, [2,3]), ActivityCompleted(result)))
        assert (datetime.now() - process.history[1].datetime).seconds == 0

        # take a decision
        decision = workflow.decide(process)
        assert isinstance(decision, CompleteProcess)
        process.history.append(DecisionEvent(decision))

class WorkflowBackendTestCase(unittest.TestCase):

    def processes_approximately_equal(self, process1, process2):
        ''' Verify the two processes are equal (except for slight timestamp difference) '''
        assert process1.id == process2.id
        assert process1.workflow == process2.workflow
        assert process1.input == process2.input
        assert len(process1.history) == len(process2.history)

        for idx,event1 in enumerate(process1.history):
            event2 = process2.history[idx]

            assert type(event1) == type(event2)

            if event2.datetime > event1.datetime:
                assert (event2.datetime - event1.datetime).seconds <= 10
            else:
                assert (event1.datetime - event2.datetime).seconds <= 10

            if isinstance(event1, DecisionEvent):
                assert event1.decision == event2.decision
            elif isinstance(event1, ActivityEvent):
                assert event1.activity == event2.activity
                assert event1.result == event2.result
            elif isinstance(event1, SignalEvent):
                assert event1.signal == event2.signal
            else:
                assert False, "Unknown event type"
        return True

    def construct_backend(self):
        raise NotImplementedError()

    def subtest_timeouts(self):
        backend = self.construct_backend()
        manager = Manager(backend, workflows=[TimeoutWorkflow])

        # Start a new TimeoutWorkflow process
        process = Process(workflow=TimeoutWorkflow)
        manager.start_process(process)

        # Decide initial activity
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decision = workflow.decide(task.process)
        assert decision == ScheduleActivity(TimeoutActivity, input=[0,0], id=1)
        manager.complete_task(task, decision)

        # Let the schedule time-out hit
        sleep(1)

        # The task should be passed back to the decider
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decision = workflow.decide(task.process)
        assert decision == ScheduleActivity(TimeoutActivity, input=[2,0], id=2)
        manager.complete_task(task, decision)

        # This time, execute the activity and time out before heartbeat
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        result = activity.execute()
        try:
            manager.complete_task(task, ActivityCompleted(result=result))
            assert False, "should have timed out and not allowed completion"
        except TimedOutException, e:
            pass

        # The task should be passed back to the decider
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decision = workflow.decide(task.process)
        assert decision == ScheduleActivity(TimeoutActivity, input=[0,5], id=3)
        manager.complete_task(task, decision)
        
        # This time, execute the activity and time out on execution
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        result = activity.execute()
        try:
            manager.complete_task(task, ActivityCompleted(result=result))
            assert False, "should have timed out and not allowed completion"
        except TimedOutException, e:
            pass

    def subtest_basic(self):
        ''' Tests the basic backend functionality (no Workflow / Activity objects involved) '''

        backend = self.construct_backend()

        # Register workflow and activity types
        backend.register_workflow('test')
        backend.register_activity('double')

        # Start a new workflow process
        backend.start_process(Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"]))
        backend.start_process(Process(id='5678', workflow='test', input=3, tags=["process-5678"]))

        # Verify we can read the process back
        assert hasattr(backend.processes(), '__iter__')
        processes = sorted(list(backend.processes()), key=lambda p: p.id)

        assert processes == [
            Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[]),
            Process(id='5678', workflow='test', input=3, tags=["process-5678"], history=[])
        ]

        # Verify we can read it back by tags
        processes = list(backend.processes(tag="foo"))
        assert processes == [Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[])]
        processes = sorted(list(backend.processes(workflow="test")), key=lambda p: p.id)
        assert processes == [
            Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[]),
            Process(id='5678', workflow='test', input=3, tags=["process-5678"], history=[])
        ]

        # Terminate the second process
        processes = list(backend.processes(tag="process-5678"))
        backend.cancel_process(processes[0])
        processes = list(backend.processes())
        assert processes == [
            Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[]),
        ]

        # Verify we get the first decision task back
        task = backend.poll_decision_task()
        assert task.process == Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[])
        
        # Execute the decision task (schedule activity)
        activity_id = '5678'
        backend.complete_decision_task(task, ScheduleActivity('double', id=activity_id, input=task.process.input))
        date_scheduled = datetime.now()

        # Verify we can read the process back
        processes = list(backend.processes())
        assert len(processes) == 1
        print processes
        print processes[0].history
        assert self.processes_approximately_equal(processes[0], Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled)
            ]))

        # Send a signal
        backend.signal_process(processes[0], 'some_signal', data={'test': 123})

        # Verify the signal is in the history
        processes = list(backend.processes())
        assert len(processes) == 1
        assert self.processes_approximately_equal(processes[0], Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123}))
            ]))

        # Verify we get the activity task back now
        task = backend.poll_activity_task()
        assert task.activity == 'double'
        assert task.input == 2

        # Simulate activity task failure
        backend.complete_activity_task(task, ActivityFailed(reason='simulated error', details='unknown'))
        date_failed = datetime.now()

        # Verify we can read the process back
        processes = list(backend.processes())
        assert len(processes) == 1
        assert self.processes_approximately_equal(processes[0], Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed)
            ]))

        # Re-schedule the task
        task = backend.poll_decision_task()
        backend.complete_decision_task(task, ScheduleActivity('double', id=activity_id, input=task.process.input))
        date_scheduled2 = datetime.now()

        # Simulate activity task abortion
        task = backend.poll_activity_task()
        backend.complete_activity_task(task, ActivityAborted(details='test'))
        date_aborted = datetime.now()

        # Verify we can read the process back
        processes = list(backend.processes())
        assert len(processes) == 1
        assert self.processes_approximately_equal(processes[0], Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled2),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityAborted(details='test'), datetime=date_aborted)
            ]))

        # Re-schedule the task
        task = backend.poll_decision_task()
        backend.complete_decision_task(task, ScheduleActivity('double', id=activity_id, input=task.process.input))
        date_scheduled3 = datetime.now()
        
        # Simulate activity task completion (perform input*2)
        task = backend.poll_activity_task()
        backend.complete_activity_task(task, ActivityCompleted(result=task.input * 2))
        date_completed = datetime.now()
        
        # Verify we can read the process back
        processes = list(backend.processes())
        assert len(processes) == 1
        assert self.processes_approximately_equal(processes[0], Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled2),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityAborted(details='test'), datetime=date_aborted),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled3),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCompleted(result=4), datetime=date_completed)
            ]))
        
        # Verify we get a decision task
        task = backend.poll_decision_task()      
        assert task.process.workflow == 'test'
        # Verify the history is there in the task as well
        assert self.processes_approximately_equal(task.process, Process(id='1234', workflow='test', input=2, tags=["process-1234", "foo"], history=[
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled),
            SignalEvent(signal=Signal('some_signal', {'test': 123})),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityFailed(reason='simulated error', details='unknown'), datetime=date_failed),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled2),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityAborted(details='test'), datetime=date_aborted),
            DecisionEvent(decision=ScheduleActivity('double', id=activity_id, input=2), datetime=date_scheduled3),
            ActivityEvent(ActivityExecution('double', activity_id, 2), result=ActivityCompleted(result=4), datetime=date_completed)
            ]))

        # Complete the decision task (complete process)
        backend.complete_decision_task(task, CompleteProcess())

        # Verify there are now no more processes
        processes = list(backend.processes())
        print processes
        assert processes == []

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
        assert task.process.history == []
        decision = workflow.decide(task.process)
        manager.complete_task(task, decision)

        # Some properties to compare later
        activity_id = decision.id
        date_scheduled = datetime.now()
        
        # Run the activity
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        assert activity == MultiplicationActivity(task)
        assert task.activity == 'Multiplication'
        assert task.input == [2,3]
        result = activity.execute()
        assert result == 6
        manager.complete_task(task, ActivityCompleted(result=result))
        date_completed = datetime.now()

        # Decide completion
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        assert task.process.workflow == 'Foo'
        assert self.processes_approximately_equal(task.process, Process(id=process.id, workflow='Foo', input=[2,3], tags=["process-1234", "foo"], history=[
            DecisionEvent(decision=ScheduleActivity('Multiplication', id=activity_id, input=[2,3]), datetime=date_scheduled),
            ActivityEvent(ActivityExecution('Multiplication', activity_id, [2,3]), result=ActivityCompleted(result=6), datetime=date_completed)
            ]))

        decision = workflow.decide(task.process)
        manager.complete_task(task, decision)

    def subtest_order(self):
        backend = self.construct_backend()
        
        # Create a manager and register the workflow
        manager = Manager(backend, workflows=[OrderWorkflow])

        #
        # Order that will fail in payment
        #
        # Start order workflow
        process = Process(workflow=OrderWorkflow, input={'items': [100, 200]}, tags=["order-1", "foo", "bar"])
        manager.start_process(process)

        read_back = list(manager.processes(workflow=OrderWorkflow))
        assert read_back == [process]
        read_back = list(manager.processes(tag="order-1"))
        assert read_back == [process]
        
        
        # Decide: -> payment processing
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Activity: abort
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityAborted())
        
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

        # Activity: complete one
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityCompleted())
        
        # Decide: -> nothing
        task = manager.next_decision()
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        assert decisions == []
        manager.complete_task(task, decisions)

        # Activity: signal other
        task2 = manager.next_activity()
        activity2 = manager.activity_for_task(task2)
        manager.signal_process(process, Signal('extra_shipment', data=300))
        
        # Decide: -> extra shipment
        task = manager.next_decision()
        decisions = workflow.decide(task.process)
        assert len(decisions) == 1
        assert isinstance(decisions[0], ScheduleActivity)
        assert decisions[0].activity == 'Shipment'
        manager.complete_task(task, decisions)

        # Activity: complete both
        task = manager.next_activity()
        activity = manager.activity_for_task(task)
        manager.complete_task(task, ActivityCompleted())
        manager.complete_task(task2, ActivityCompleted())
        
        # Decide: -> complete
        task = manager.next_decision()
        print task.process.history
        workflow = manager.workflow_for_task(task)
        decisions = workflow.decide(task.process)
        manager.complete_task(task, decisions)

        # Verify completion
        print decisions
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
        worker = WorkerThread(ActivityWorker(worker_mgr))
        worker.start()

        # Start a new FooWorkflow process
        process = Process(workflow=FooWorkflow, input=[2,3])
        manager.start_process(process)

        assert len(list(manager.processes())) == 1

        # We expect this to take no more than 4 seconds
        for _ in range(0,4):
            if len(list(manager.processes())) == 0:
                break
            sleep(1)

        decider.join(1)
        worker.join(1)
        assert len(list(manager.processes())) == 0