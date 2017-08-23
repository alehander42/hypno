from errors import HypnoError

class Env:
    def __init__(self, values=None, parent=None):
        self.values = values or {}
        self.parent = parent
        if parent is None:
            self.base_env = self
        else:
            self.base_env = parent.base_env

    def __getitem__(self, name):
        scope = self
        while scope != None:
            if name in scope.values:
                return scope.values[name]
            scope = scope.parent
        raise HypnoError('%s missing' % name)

    def __setitem__(self, name, value):
    	self.values[name] = value
