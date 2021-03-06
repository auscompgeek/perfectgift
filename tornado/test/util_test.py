# coding: utf-8
from __future__ import absolute_import, division, print_function, with_statement
import sys

from tornado.escape import utf8
from tornado.util import raise_exc_info, Configurable, u, exec_in, ArgReplacer
from tornado.test.util import unittest

try:
	from cStringIO import StringIO  # py2
except ImportError:
	from io import StringIO  # py3


class RaiseExcInfoTest(unittest.TestCase):
	def test_two_arg_exception(self):
		# This test would fail on python 3 if raise_exc_info were simply
		# a three-argument raise statement, because TwoArgException
		# doesn't have a "copy constructor"
		class TwoArgException(Exception):
			def __init__(self, a, b):
				super(TwoArgException, self).__init__()
				self.a, self.b = a, b

		try:
			raise TwoArgException(1, 2)
		except TwoArgException:
			exc_info = sys.exc_info()
		try:
			raise_exc_info(exc_info)
			self.fail("didn't get expected exception")
		except TwoArgException as e:
			self.assertIs(e, exc_info[1])


class TestConfigurable(Configurable):
	@classmethod
	def configurable_base(cls):
		return TestConfigurable

	@classmethod
	def configurable_default(cls):
		return TestConfig1


class TestConfig1(TestConfigurable):
	def initialize(self, a=None):
		self.a = a


class TestConfig2(TestConfigurable):
	def initialize(self, b=None):
		self.b = b


class ConfigurableTest(unittest.TestCase):
	def setUp(self):
		self.saved = TestConfigurable._save_configuration()

	def tearDown(self):
		TestConfigurable._restore_configuration(self.saved)

	def checkSubclasses(self):
		# no matter how the class is configured, it should always be
		# possible to instantiate the subclasses directly
		self.assertIsInstance(TestConfig1(), TestConfig1)
		self.assertIsInstance(TestConfig2(), TestConfig2)

		obj = TestConfig1(a=1)
		self.assertEqual(obj.a, 1)
		obj = TestConfig2(b=2)
		self.assertEqual(obj.b, 2)

	def test_default(self):
		obj = TestConfigurable()
		self.assertIsInstance(obj, TestConfig1)
		self.assertIs(obj.a, None)

		obj = TestConfigurable(a=1)
		self.assertIsInstance(obj, TestConfig1)
		self.assertEqual(obj.a, 1)

		self.checkSubclasses()

	def test_config_class(self):
		TestConfigurable.configure(TestConfig2)
		obj = TestConfigurable()
		self.assertIsInstance(obj, TestConfig2)
		self.assertIs(obj.b, None)

		obj = TestConfigurable(b=2)
		self.assertIsInstance(obj, TestConfig2)
		self.assertEqual(obj.b, 2)

		self.checkSubclasses()

	def test_config_args(self):
		TestConfigurable.configure(None, a=3)
		obj = TestConfigurable()
		self.assertIsInstance(obj, TestConfig1)
		self.assertEqual(obj.a, 3)

		obj = TestConfigurable(a=4)
		self.assertIsInstance(obj, TestConfig1)
		self.assertEqual(obj.a, 4)

		self.checkSubclasses()
		# args bound in configure don't apply when using the subclass directly
		obj = TestConfig1()
		self.assertIs(obj.a, None)

	def test_config_class_args(self):
		TestConfigurable.configure(TestConfig2, b=5)
		obj = TestConfigurable()
		self.assertIsInstance(obj, TestConfig2)
		self.assertEqual(obj.b, 5)

		obj = TestConfigurable(b=6)
		self.assertIsInstance(obj, TestConfig2)
		self.assertEqual(obj.b, 6)

		self.checkSubclasses()
		# args bound in configure don't apply when using the subclass directly
		obj = TestConfig2()
		self.assertIs(obj.b, None)


class UnicodeLiteralTest(unittest.TestCase):
	def test_unicode_escapes(self):
		self.assertEqual(utf8(u('\u00e9')), b'\xc3\xa9')


class ExecInTest(unittest.TestCase):
	# This test is python 2 only because there are no new future imports
	# defined in python 3 yet.
	@unittest.skipIf(sys.version_info >= print_function.getMandatoryRelease(),
					 'no testable future imports')
	def test_no_inherit_future(self):
		# This file has from __future__ import print_function...
		f = StringIO()
		print('hello', file=f)
		# ...but the template doesn't
		exec_in('print >> f, "world"', dict(f=f))
		self.assertEqual(f.getvalue(), 'hello\nworld\n')


class ArgReplacerTest(unittest.TestCase):
	def setUp(self):
		def function(x, y, callback=None, z=None):
			pass
		self.replacer = ArgReplacer(function, 'callback')

	def test_omitted(self):
		self.assertEqual(self.replacer.replace('new', (1, 2), dict()),
						 (None, (1, 2), dict(callback='new')))

	def test_position(self):
		self.assertEqual(self.replacer.replace('new', (1, 2, 'old', 3), dict()),
						 ('old', [1, 2, 'new', 3], dict()))

	def test_keyword(self):
		self.assertEqual(self.replacer.replace('new', (1,),
											   dict(y=2, callback='old', z=3)),
						 ('old', (1,), dict(y=2, callback='new', z=3)))
