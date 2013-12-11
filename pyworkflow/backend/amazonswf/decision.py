import json

from ...decision import ScheduleActivity, CompleteProcess, CancelProcess, StartChildProcess

class AmazonSWFDecision(object):
    def __init__(self, decision):
        if isinstance(decision, ScheduleActivity):
            description = self.schedule_activity_description(decision)
        elif isinstance(decision, CompleteProcess):
            description = self.complete_process_description(decision)
        elif isinstance(decision, CancelProcess):
            description = self.cancel_process_description(decision)
        elif isinstance(decision, StartChildProcess):
            description = self.start_child_process_description(decision)
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
                "input": json.dumps(decision.input) if decision.input else None,
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
        
    def start_child_process_description(self, decision):
        return {
            "decisionType": "StartChildWorkflowExecution",
            "startChildWorkflowExecutionDecisionAttributes": {
                'workflowType': {
                    'name': decision.process.workflow,
                    'version': "1.0"
                },
                'workflowId': decision.process.id,
                'input': json.dumps(decision.process.input),
                'tagList': decision.process.tags
            }
        }