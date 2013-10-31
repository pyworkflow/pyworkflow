AMAZON_SWF_ACCESS_KEY_ID = None
AMAZON_SWF_SECRET_ACCESS_KEY = None
AMAZON_SWF_DOMAIN = None
AMAZON_SWF_REGION = 'us-east-1'

try:
    from test_settings import *
except:
    raise Exception('Please supply test/settings.py with configuration flags')

import unittest

from ..test import WorkflowTestCase
from . import AmazonSWFBackend

class AmazonSWFBackendTestCase(WorkflowTestCase):
	def setUp(self):
		self.backend = AmazonSWFBackend(AMAZON_SWF_ACCESS_KEY_ID, AMAZON_SWF_SECRET_ACCESS_KEY, region=AMAZON_SWF_REGION, domain=AMAZON_SWF_DOMAIN)
		for p in self.backend.processes():
			self.backend.cancel_process(p)

	def test_basic(self):
		self.subtest_basic(self.backend)