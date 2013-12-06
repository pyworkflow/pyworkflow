from blinker import Signal
from .. import Backend
from ...decision import *
from ...activity import *

class BlinkerBackend(Backend):
    # Blinker signals
    on_complete_decision_task = Signal()
    on_complete_activity_task = Signal()

    on_activity_scheduled = Signal()
    on_activity_started = Signal()
    on_activity_completed = Signal()
    on_activity_canceled = Signal()
    on_activity_aborted = Signal()
    on_activity_failed = Signal()
    on_activity_timedout = Signal()

    on_process_started = Signal()
    on_process_completed = Signal()
    on_process_canceled = Signal()
    on_process_signaled = Signal()


    def __init__(self, parent):
        self.parent = parent

    # Pipe through most (non-event-generating) requests directly to parent backend

    def register_workflow(self, *args, **kwargs):
        return self.parent.register_workflow(*args, **kwargs)

    def register_activity(self, *args, **kwargs):
        return self.parent.register_activity(*args, **kwargs)

    def processes(self, *args, **kwargs):
        return self.parent.processes(*args, **kwargs)

    def poll_activity_task(self, *args, **kwargs):
        return self.parent.poll_activity_task(*args, **kwargs)

    def poll_decision_task(self, *args, **kwargs):
        task = self.parent.poll_decision_task(*args, **kwargs)
        if task:
            # check if any activities have timed out
            for event in task.process.unseen_events():
                if hasattr(event, 'result') and isinstance(event.result, ActivityTimedOut):
                    BlinkerBackend.on_activity_timedout.send(self, event.activity, **event.result.__dict__)
        return task
    
    def heartbeat_activity_task(self, *args, **kwargs):
        return self.parent.heartbeat_activity_task(*args, **kwargs)

    # For the events we're interested in, emit signals

    def start_process(self, process):
        BlinkerBackend.on_process_started.send(self, process=process)
        return self.parent.start_process(process)
    
    def signal_process(self, process, signal, data=None):
        BlinkerBackend.on_process_signaled.send(self, process=process, signal=signal, data=data)
        return self.parent.signal_process(process, signal, data=data)

    def cancel_process(self, process, details=None, reason=None):
        BlinkerBackend.on_process_canceled.send(self, process=process, details=details, reason=reason)
        return self.parent.cancel_process(process, details=details, reason=reason)

    def decision_signal(self, decision):
        mapping = {
            ScheduleActivity: BlinkerBackend.on_activity_scheduled,
            CancelActivity: BlinkerBackend.on_activity_canceled,
            CompleteProcess: BlinkerBackend.on_process_completed,
            CancelProcess: BlinkerBackend.on_process_canceled
        }

        return mapping[decision.__class__]

    def activity_result_signal(self, result):
        mapping = {
            ActivityCompleted: BlinkerBackend.on_activity_completed,
            ActivityAborted: BlinkerBackend.on_activity_aborted,
            ActivityFailed: BlinkerBackend.on_activity_failed
        }

        return mapping[result.__class__]

    def complete_decision_task(self, task, decisions):
        BlinkerBackend.on_complete_decision_task.send(self, task=task, decisions=decisions)
        
        for decision in decisions if type(decisions) == list else [decisions]:
            self.decision_signal(decision).send(self, process=task.process, **decision.__dict__)

        return self.parent.complete_decision_task(task, decisions)

    def complete_activity_task(self, task, result=None):
        BlinkerBackend.on_complete_activity_task.send(self, task=task, result=result)
        
        self.activity_result_signal(result).send(self, activity=task.activity, process_id=task.process_id, input=task.input, **result.__dict__)
        
        return self.parent.complete_activity_task(task, result=result)
