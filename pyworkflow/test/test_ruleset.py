import unittest
from ..managed.workflow.ruleset import RuleSetMetaclass
from ..managed.workflow import rules


class TestRuleDecorator(unittest.TestCase):

  def test_ruleset_metaclass(self):
    class TestCls(object):
      __metaclass__ = RuleSetMetaclass

      @rules.rule(match=lambda x: x>0)
      def handle_everything(self, x, _):
        return x+1

    assert len(TestCls.ruleset) == 1
    rule = TestCls.ruleset[0]

    test_obj = TestCls()
    assert test_obj.handle_everything.match(1)
    assert not test_obj.handle_everything.match(0)
    assert test_obj.handle_everything(None, 3, None) == 4

if __name__ == '__main__':
  unittest.main()
