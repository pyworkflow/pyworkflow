class classproperty(object):
  '''Implements both @property and @classmethod behavior.'''

  def __init__(self, getter):
    self.getter = getter

  def __get__(self, instance, owner):
    return self.getter(instance) if instance else self.getter(owner)
