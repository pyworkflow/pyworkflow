from base import Workflow
from utils import ensure_iter, flatten, unique

class DefaultWorkflow(Workflow):
    def initiate(self, process):
        raise NotImplementedError()

    def respond_to_completed_activity(self, process, activity_execution, result):
        raise NotImplementedError()

    def respond_to_interrupted_activity(self, process, activity_execution, details):
        raise NotImplementedError()

    def respond_to_signal(self, process, signal):
        raise NotImplementedError()

    def respond_to_timer(self, process, timer):
        raise NotImplementedError()

    def respond_to_child_process(self, process, child_process_id, workflow, result, tags):
        raise NotImplementedError()

    def handle_event(self, event, process):
        if event.type == 'process_started':
            return self.initiate(process)
        elif event.type == 'activity':
            if event.result.type == 'completed':
                return self.respond_to_completed_activity(process, event.activity_execution, event.result.result)
            else:
                return self.respond_to_interrupted_activity(process, event.activity_execution, event.result)
        elif event.type == 'signal':
            return self.respond_to_signal(process, event.signal)
        elif event.type == 'timer':
            return self.respond_to_timer(process, event.timer)
        elif event.type == 'child_process':
            return self.respond_to_child_process(process, event.process_id, event.workflow, event.result, event.tags)

    def decide(self, process):
        handler = lambda ev: filter(bool, ensure_iter(self.handle_event(ev, process)))
        decisions = map(handler, process.unseen_events()) # list of lists of decisions
        return unique(flatten(decisions))