import unittest

import pymongo

from datastore.core import DictDatastore
from datastore.mongo import MongoDatastore

from ...test import WorkflowBackendTestCase
from . import DatastoreBackend

class DatastoreBackendTestCase(WorkflowBackendTestCase):
    def setUp(self):
        super(DatastoreBackendTestCase, self).setUp()
        conn = pymongo.Connection('127.0.0.1')
        ds = MongoDatastore(conn.testpyworkflow)
        db = pymongo.database.Database(conn, 'testpyworkflow')
        for coll in db.collection_names():
            if coll.startswith('system'):
                continue
                
            print "Dropping MongoDB collection %s" % (coll)
            db.drop_collection(coll)

        self.backend = DatastoreBackend(ds)

    def tearDown(self):
        super(DatastoreBackendTestCase, self).tearDown()

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