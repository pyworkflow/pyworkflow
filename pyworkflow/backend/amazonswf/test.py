AMAZON_SWF_ACCESS_KEY_ID = None
AMAZON_SWF_SECRET_ACCESS_KEY = None
AMAZON_SWF_DOMAIN = None
AMAZON_SWF_REGION = 'us-east-1'

try:
    from test_settings import *
except:
    raise Exception('Please supply test_settings.py with configuration flags')

import unittest

from boto import config

from ...defaults import Defaults
from ...test import WorkflowBackendTestCase
from . import AmazonSWFBackend

import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)

class AmazonSWFBackendTestCase(WorkflowBackendTestCase):
    def setUp(self):
        super(AmazonSWFBackendTestCase, self).setUp()

        self.backends = []
        backend = self.construct_backend()
        for p in backend.processes():
            backend.cancel_process(p)

    def tearDown(self):
        super(AmazonSWFBackendTestCase, self).tearDown()

    def construct_backend(self):
        backend = AmazonSWFBackend(AMAZON_SWF_ACCESS_KEY_ID, AMAZON_SWF_SECRET_ACCESS_KEY, region=AMAZON_SWF_REGION, domain=AMAZON_SWF_DOMAIN)
        self.backends.append(backend)
        return backend

    def test_basic(self):
        self.subtest_basic()

    def test_managed(self):
        self.subtest_managed()

    def test_timeouts(self):
        self.subtest_timeouts()

    def test_order(self):
        self.subtest_order()

class AmazonSWFBackendThreadTestCase(WorkflowBackendTestCase):
    def setUp(self):
        super(AmazonSWFBackendThreadTestCase, self).setUp()

        # Make long-polling connections time out really quickly
        # Note: this will break in the normal case, since SWF will continue to
        # assign tasks to identities that have already closed their connection
        try:
            config.add_section('Boto')
        except:
            pass
        config.set('Boto', 'http_socket_timeout', '5')

        Defaults.DECISION_TIMEOUT = 1

        self.backends = []
        backend = self.construct_backend()
        for p in backend.processes():
            backend.cancel_process(p)

    def tearDown(self):
        for b in self.backends:
            # trick the backend into retrying connections that will fail
            b._swf.host = 'localhost'
            b._swf.close()
        
        config.set('Boto', 'http_socket_timeout', '70')
        Defaults.DECISION_TIMEOUT = 60

        super(AmazonSWFBackendThreadTestCase, self).tearDown()

    def construct_backend(self):
        backend = AmazonSWFBackend(AMAZON_SWF_ACCESS_KEY_ID, AMAZON_SWF_SECRET_ACCESS_KEY, region=AMAZON_SWF_REGION, domain=AMAZON_SWF_DOMAIN)
        self.backends.append(backend)
        return backend

    def test_threads(self):
        self.subtest_threads()