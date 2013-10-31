from .. import Backend

class DatastoreBackend(Backend):
    def poll_activity(self):
        obj = ds.query(Query().filter('state','=','SCHEDULED'))
        return ActivityTask(obj.data)

    def poll_decision(self):
        obj = ds.query(Query().filter('state','!=','STARTED').filter('state','!=','SCHEDULED'))
        return DecisionTask(obj.data)

    def record_event(self, event):
    	self.process.add_event(event)
    	mgr = Manager(self.datastore, model=DatastoreProcess)
    	mgr.put(DatastoreProcess.from_process(self.process))

    def heartbeat(self):
    	self.record_event(Event(HEARTBEAT))

    def complete_activity(self, activity_task, result):
    	self.record_event(Event(ACTIVITY_COMPLETE, result))

    def fail_activity(self, activity_task, reason):
    	self.record_event(Event(ACTIVITY_COMPLETE, result))

    def abort_activity(self, activity_task, reason):
    	self.record_event(Event(ACTIVITY_COMPLETE, result))