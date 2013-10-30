from .. import Backend

class DatastoreBackend(Backend):
    def poll_activity(self):
        obj = ds.query(Query().filter('state','=','SCHEDULED'))
        return ActivityTask(obj.data)

    def poll_decision(self):
        obj = ds.query(Query().filter('state','!=','STARTED').filter('state','!=','SCHEDULED'))
        return DecisionTask(obj.data)