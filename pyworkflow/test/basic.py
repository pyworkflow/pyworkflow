def test_basic():
    run_with_backend(DatastoreBackend(DictDatastore()))
    
def run_with_backend(backend):
    backend.register_workflow('test')
    backend.register_activity('double')

    backend.start_process(workflow='test', input=1)

    decision = backend.poll_decision_task()
    assert decision.process.workflow == 'test'
    assert decision.history == []

    backend.schedule_activity(decision.process, 'double', decision.process.input)

    activity = backend.poll_activity_task()
    assert activity.process.workflow == 'test'
    assert activity.activity == 'double'
    assert activity.input == 1

    backend.complete_activity(activity.process, result=activity.input * 2)

    decision = backend.poll_decision_task()
    assert decision.process.workflow == 'test'
    assert decision.history == [Event(Event.Type.SCHEDULED, 'double', 1), Event(Event.Type.COMPLETED, 'double', 2)]
