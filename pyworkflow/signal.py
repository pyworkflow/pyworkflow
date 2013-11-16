class Signal(object):
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return 'Signal(%s, %s)' % (self.name, self.data)