# pyworkflow

## unified framework for workflow processes

pyworkflow allows for the easy implementation of workflows, and handling the execution
of workflow processes, across multiple backends. Its architectural design is largely
based on Amazon SWF, and pyworkflow.amazonswf was the first backend to be written
for pyworkflow. However, different backends can be used allowing to leverage the full
power of workflows without committing to any single execution backend in terms of
implementation.

## API

Workflows determine the particular flow of a process through a set of activities.
The first step is to implement activities by overriding the Activity, like so:

````
from pyworkflow.activity import Activity, ActivityAborted

class FooActivity(Activity):

	@classmethod
	def execute(cls, task, worker):
		worker.heartbeat()

		if task.input < 10:
			return task.input * 2 # short for ActivityCompleted(result=task.input * 2)
		elif task.input:
			return ActivityAborted(reason='input out of bounds')
		else:
			raise Exception('no input') # short for ActivityFailed(exception=Exception('no input'))
````

Next, we define our workflows that guide processes through the activities. A
workflow extends the Workflow class and overrides its decide() method:

````
from pyworkflow.workflow import Workflow
from pyworkflow.decision import CompleteProcessDecision

class BarWorkflow(Workflow):

	@classmethod
	def decide(cls, process):
		if foo_bar(process.history):
			return FooActivity # shorthand for ScheduleActivityDecision(FooActivity)
		else:
			return CompleteProcessDecision()
````

## Design considerations

### Workflow
A Workflow manages the execution path of a Process for that workflow, which
is a consecutive application of Activities on a certain input. The invocation of a
Workflow is started when a process for that Workflow is created. 

### Process
A Process is a particular execution of a Workflow. It contains both the input and
the execution history.

### Task

What is an activity task?
- The required execution of an activity A on input x
- Task contains execution environment state (e.g. SWF task token)

What is a decision task?
- The decision on a next step for a process P in workflow W
- Task contains execution environment state (e.g. SWF task token)

Should a task implement control?
- Should Activity.execute(task) be able to simply call task.complete(), or should activity return the result and let the worker handle it?
- Activity needs to be able to send heartbeats to the invoker, somehow. Could be through task?
- Note: Activity.execute() is always run by an ActivityWorker. Activity can send heartbeats to worker.
- Worker can handle result from Activity.execute() by communicating with backend. Worker then becomes re

````
# Scenario 1: Task facilitates execution control

class FooActivity(Activity):
	@classmethod
	def execute(cls, task):
		task.heartbeat()
		task.complete(task.input * 2)

class ActivityWorker(object):
	def run():
		task = backend.next_activity_task()
		FooActivity.execute(task)
````


````
# Scenario 2: Execution control is responsibility of Worker.

class FooActivity(Activity):
	@classmethod
	def execute(cls, task, worker):
		worker.heartbeat(task)
		return task.input * 2

class ActivityWorker(object):
	def heartbeat(task):
		backend.heartbeat(task.id)

	def run():
		task = backend.next_activity_task()
		result = FooActivity.execute(task, self)
		backend.complete(task.id, result)
````


### Activity

What does it mean for an Activity to execute?
- an activity is executed as a task T in a workflow process P
- task T is to perform function f() of the activity on input x
- T can complete with a result, abort with a reason, or fail with an error
- the result will be saved on process P
- the execution has to send out a heartbeat at intervals to the invoker
- T can signal other tasks (may not be exclusive to Activity execution)

Does Activity have to be strictly aware of workflow process?
- If the responsibility of recording the result of task T onto P is placed
  elsewhere, then NO

Does it make sense for Activity to be responsible for recording the result of task T?
- Activity is the execution of task T. It is being executed by a worker.
  Therefore it makes most sense for the worker to handle the result.

Does Activity have to be aware of the invoker?
- There needs to be some two-way communication, because the invoker needs to
  receive heartbeats.
- Can the heartbeats be sent through the task T?


## About

### License

workflow is under the MIT License.

### Contact

workflow is written by [Willem Bult](https://github.com/willembult).

Project Homepage:
[https://github.com/RentMethod/workflow](https://github.com/RentMethod/workflow)

Feel free to contact me. But please file issues in github first. Thanks!

## Examples

## API