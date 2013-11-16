import json

from ...decision import ScheduleActivity, CompleteProcess, CancelProcess

class AmazonSWFDecision(object):
    def __init__(self, decision):
        if isinstance(decision, ScheduleActivity):
            description = self.schedule_activity_description(decision)
        elif isinstance(decision, CompleteProcess):
            description = self.complete_process_description(decision)
        elif isinstance(decision, CancelProcess):
            description = self.cancel_process_description(decision)
        else:
            raise Exception('Invalid decision type')

        self.description = description

    def schedule_activity_description(cls, decision):
        return {
            "decisionType": "ScheduleActivityTask",
            "scheduleActivityTaskDecisionAttributes": {
                "activityId": str(decision.id),
                "activityType": {
                  "name": decision.activity,
                  "version": "1.0",
                },
                "control": None,
                #"heartbeatTimeout": SWF_TASK_HEARTBEAT_TIMEOUT if step.autocomplete else SWF_TASK_SCHEDULE_TO_CLOSE_TIMEOUT,
                "input": json.dumps(decision.input) if decision.input else None,
                #"scheduleToCloseTimeout": SWF_TASK_SCHEDULE_TO_CLOSE_TIMEOUT,
                #"scheduleToStartTimeout": SWF_TASK_SCHEDULE_TO_START_TIMEOUT,
                #"startToCloseTimeout": str(step.timeout) if step.timeout else SWF_TASK_START_TO_CLOSE_TIMEOUT,
                "taskList": {
                    "name": decision.category or "default"
                }
            }
        }

    def complete_process_description(self, decision):
        return {
            "decisionType": "CompleteWorkflowExecution",
            "completeWorkflowExecutionDecisionAttributes": {
                "result": json.dumps(decision.result)
            }
        }

    def cancel_process_description(self, decision):
        return {
            "decisionType": "CancelWorkflowExecution",
            "cancelWorkflowExecutionDecisionAttributes": {
                "details": decision.details
            }
        }
        