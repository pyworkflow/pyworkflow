import threading
import logging
import traceback

class WorkerThread(threading.Thread):
    '''
    Thread that repeatedly runs a decider/activity worker.
    Inherent isolated state contained in this class.
    '''

    def __init__(self, worker, logger=None):
        super(WorkerThread, self).__init__()

        # Internal events
        self.stop = threading.Event()

        # Our functional actors
        self.worker = worker
        self.logger = logger or logging.getLogger('workflow')

    def run(self):
        self.logger.info("Worker started: %s" % (self.worker))

        while not self.stop.isSet():
            try:
                self.worker.step(logger=self.logger)
            except Exception, e:
                self.logger.error("Worker %s encountered error while getting activity: %s" % (self.worker, traceback.format_exc()))

        self.logger.info("Worker finished: %s" % (self.worker))

    def join(self, timeout=None):
        self.stop.set()
        super(WorkerThread, self).join(timeout)