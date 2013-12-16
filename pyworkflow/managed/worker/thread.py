import threading
import logging
import traceback
from time import sleep

class WorkerThread(threading.Thread):
    '''
    Thread that repeatedly runs a decider/activity worker.
    Inherent isolated state contained in this class.
    '''

    def __init__(self, worker, logger=None, delay_on_idle=1):
        super(WorkerThread, self).__init__()

        self.delay_on_idle = delay_on_idle

        # Internal events
        self.stop = threading.Event()

        # Our functional actors
        self.worker = worker
        self.logger = logger or logging.getLogger('workflow')

    def run(self):
        self.logger.info("Worker started: %s" % (self.worker))

        while not self.stop.isSet():
            try:
                if not self.worker.step(logger=self.logger):
                    sleep(self.delay_on_idle)
            except Exception, e:
                self.logger.exception("Worker %s encountered error while performing step" % (self.worker))

        self.logger.info("Worker finished: %s" % (self.worker))

    def join(self, timeout=None):
        self.stop.set()
        super(WorkerThread, self).join(timeout)