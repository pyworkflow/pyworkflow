# pyworkflow

## unified framework for workflow processes

pyworkflow allows for the easy implementation of workflows, and handling the execution
of workflow processes, across multiple backends. Its architectural design is largely
based on Amazon SWF, and pyworkflow.amazonswf was the first backend to be written
for pyworkflow. However, different backends can be used allowing to leverage the full
power of workflows without committing to any single execution backend in terms of
implementation.

## Usage

Workflows determine the particular flow of a process through a set of activities.
The first step is to implement activities by overriding the Activity, like so:

````
from pyworkflow.activity import Activity, ActivityAborted

class FooActivity(Activity):

	@classmethod
	def execute(cls, input, heartbeat):
		heartbeat()

		if type(input) == int:
			if input < 10:
				return input * 2
			else:
				raise ActivityAborted("input out of bounds")
		else:
			raise Exception("don't know what to do")

````

Next, we define our workflows that guide processes through the activities. A
workflow extends the Workflow class and overrides its decide() method:

````
from pyworkflow.workflow import Workflow
from pyworkflow.decision import CompleteProcess

class BarWorkflow(Workflow):

	activities = [FooActivity]

	@classmethod
	def decide(cls, process):
		if foo_bar(process.history):
			return FooActivity
		else:
			return ProcessCompletion()
````

Then create a manager with a particular backend and register our workflows

````
from pyworkflow.manager import Manager
from pyworkflow.foo import FooBackend

manager = Manager(backend=FooBackend())
manager.register_workflow(BarWorkflow)
````

To start an activity worker (in a separate process; is blocking)
````
from pyworkflow.worker import ActivityWorker
ActivityWorker(backend=manager.backend).run()
````

Or a decider:
````
from pyworkflow.decider import Decider
Decider(backend=manager.backend).run()
````

## Architecture

### Core

Idea: WorkflowType should be the meta class for Workflow, similar to ActivityType for Activity. Then a description object
can be used to communicate with the backend (register_workflow and process.workflow)

### Workflow

A Workflow manages the execution path of a Process for that workflow, which
is a consecutive application of Activities on a certain input. The invocation of a
Workflow is started when a process for that Workflow is created. 

### Process

A Process is a particular execution of a Workflow. It contains details about the input
and history of the execution flow.

### Activity

Activity specifies the logic of some business function. It is used to execute ActivityTasks. It is invoked by an ActivityWorker and has a reference to that worker. It may need to let the ActivityWorker know it's still active from time to time by sending heartbeats.

### ActivityTask

An ActivityTask stipulates the execution of some Activity on some input. It is a fully independent entity. It does not contain a reference to the process it is a part of, nor to the invoker who executes it. It is the entity that is exchanged between the backend and the worker as an identifier 

### ActivityWorker

ActivityWorker executes an ActivityTask it gets from the backend by instantiating and executing the specified Activity and keeping the backend informed about its progress and results.


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