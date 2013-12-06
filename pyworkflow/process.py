from uuid import uuid4
from workflow import Workflow
from event import DecisionEvent, ActivityEvent
from activity import ActivityExecution
from decision import ScheduleActivity

class Process(object):
    def __init__(self, workflow=None, id=None, input=None, tags=None, history=None, parent=None):
        try:
            self._workflow = workflow.name
        except:
            self._workflow = str(workflow)

        self._id = id or str(uuid4())
        self._parent = None
        self._input = input
        self._history = history or []
        self._tags = tags or []
        
    @property
    def workflow(self):
        return self._workflow

    @property
    def id(self):
        return self._id

    @property
    def parent(self):
        return self._parent

    @property
    def input(self):
        return self._input

    @property
    def history(self):
        return self._history
    
    @property
    def tags(self):
        return self._tags

    def unseen_events(self):
        def before_decision(iterable):
            event = next(iterable, None)
            return [] if not event or hasattr(event, 'decision') else [event] + before_decision(iterable)

        return before_decision(reversed(self.history))

    def unfinished_activities(self):
        def unfinished(iterable):
            event = next(iterable, None)
            if event is None:
                return []
            elif hasattr(event, 'decision') and hasattr(event.decision, 'activity'):
                return unfinished(iterable) + [ActivityExecution(event.decision.activity, event.decision.id, event.decision.input)]
            elif hasattr(event, 'activity') and hasattr(event, 'result'):
                return filter(lambda x: x != event.activity, unfinished(iterable))
            else:
                return unfinished(iterable)

        return unfinished(reversed(self.history))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return 'Process(%s, %s, %s, %s)' % (self.workflow, self.id, self.input, self.tags)