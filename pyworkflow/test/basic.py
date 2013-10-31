class WorkflowTestCase(TestCase):
    def basic_test(backend):
        backend.register_workflow('test')
        backend.register_activity('double')

        backend.start_process(workflow='test', input=2)

        task = backend.poll_decision_task()
        assert task.process.workflow == 'test'
        assert task.process.history == []

        backend.schedule_activity(task, 'double', input=task.process.input)

        task = backend.poll_activity_task()
        assert task.process.workflow == 'test'
        assert task.activity == 'double'
        assert task.input == 2

        backend.complete_activity(task, result=task.input * 2)

        task = backend.poll_decision_task()
        assert task.process.workflow == 'test'
        assert task.process.history == [Event(Event.Type.SCHEDULED, 'double', input=2), Event(Event.Type.COMPLETED, 'double', result=4)]

def run_managed(backend):

    class MultiplyActivity(Activity):
        @classmethod
        def execute(cls, input, context):
            context.heartbeat()

            if not type(input) is tuple or len(input) != 2:
                raise ValueError('invalid input; expected tuple of length 2')
            
            return input[0] * input[1]

    class FooWorkflow(Workflow):
        activities = [MultiplyActivity]

        @classmethod
        def schedule(cls, process):
            if len(process.history) == 0:
                return ScheduleActivity(MultiplyActivity, input=process.input)
            else:
                return ProcessComplete()


    # Create a manager and register the workflow
    manager = Manager(backend)
    manager.register_workflow(FooWorkflow)

    # Start a new foo process
    manager.start_process('FooWorkflow', input=(2,3))

    # Decide initial activity
    task = manager.poll_decision_task()
    assert task.workflow == FooWorkflow
    assert task.process.input == (2,3)
    assert task.process.history == []
    decision = task.workflow.schedule(task.process)
    manager.complete_task(task, decision)
    
    # Get the ActivityTask
    task = manager.poll_activity_task()
    assert task.activity == MultiplyActivity
    assert task.input == (2,3)
    result = task.activity.execute(task.input)
    assert result == 6
    manager.complete_task(task, result)

    # Decide completion
    task = manager.poll_decision_task()
    assert task.workflow == FooWorkflow
    assert task.process.history == [Event(Event.Type.SCHEDULED, 'double', 1), Event(Event.Type.COMPLETED, 'double', 2)]
    decision = task.workflow.schedule(task.process)
    manager.complete_task(task, decision)
    