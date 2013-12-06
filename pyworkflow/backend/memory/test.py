import unittest

from ...test import WorkflowBackendTestCase
from . import MemoryBackend

class MemoryBackendTestCase(WorkflowBackendTestCase):
    def setUp(self):
        super(MemoryBackendTestCase, self).setUp()
        self.backend = MemoryBackend()

    def tearDown(self):
        super(MemoryBackendTestCase, self).tearDown()

    def construct_backend(self):
        return self.backend

    def test_basic(self):
        self.subtest_basic()
        
    def test_managed(self):
        self.subtest_managed()
    
    def test_timeouts(self):
        self.subtest_timeouts()
    
    def test_order(self):
        self.subtest_order()
    
    def test_threads(self):
        self.subtest_threads()
    