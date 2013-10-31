import unittest

from ..task import ScheduleActivity, ActivityCompleted, CompleteProcess
from ..process import Process, Event

class WorkflowTestCase(unittest.TestCase):
    def subtest_basic(self, backend):
        backend.register_workflow('test')
        backend.register_activity('double')

        backend.start_process(Process(workflow='test', input=2))

        task = backend.poll_decision_task()
        assert task.process.workflow == 'test'
        assert task.process.history == []
        assert task.process.input == 2

        backend.complete_decision_task(task, ScheduleActivity('double', input=task.process.input))

        task = backend.poll_activity_task()
        assert task.activity == 'double'
        assert task.input == 2

        backend.complete_activity_task(task, ActivityCompleted(result=task.input * 2))

        task = backend.poll_decision_task()
        assert task.process.workflow == 'test'
        #assert task.process.history == [Event(Event.Type.SCHEDULED, 'double', input=2), Event(Event.Type.COMPLETED, 'double', result=4)]

        backend.complete_decision_task(task, CompleteProcess())

        processes = backend.processes()
        assert processes == []

