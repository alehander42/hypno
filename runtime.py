from env import Env

class HypnoValue:
    '''
    A base class for each Hypno value
    subclasses will contain its type, its fields, methods and state
    '''
    def __init__(self, hypno_type, fields=None):
        self.fields = fields or {}
        self.hypno_type = hypno_type

    def render(self):
        return 'object<%s>' % self.hypno_type.render()

class HypnoClass(HypnoValue):
    '''
    Contains class info
    '''
    def __init__(self, label, base=None, methods=None, hypno_type=False):
        if not hypno_type:
            self.hypno_type = HYPNO_TYPE
        else:
            self.hypno_type = self
        self.fields = {}
        self.label = label
        self.base = base
        self.methods = methods or {}

    def render(self):
        return 'class<%s>' % self.label

HYPNO_TYPE   = HypnoClass('type', base=None, hypno_type=True)
HYPNO_OBJECT = HypnoClass('object', base=None)
HYPNO_TYPE.base = HYPNO_OBJECT # chicken egg
HYPNO_INT    = HypnoClass('int', base=HYPNO_OBJECT)
HYPNO_STRING = HypnoClass('str', base=HYPNO_OBJECT)
HYPNO_BOOL   = HypnoClass('bool', base=HYPNO_OBJECT)
HYPNO_NONE   = HypnoValue(hypno_type=HypnoClass('NoneType', base=HYPNO_OBJECT))

class HypnoBasic(HypnoValue):
    '''
    For simple types , just a wrapper around the python value
    hypno_type contains the value of its class
    '''
    def __init__(self, value):
        self.value = value

class HypnoInt(HypnoBasic):
    hypno_type = HYPNO_INT

    def render(self):
        return '%d' % self.value

class HypnoString(HypnoBasic):
    hypno_type = HYPNO_STRING

    def render(self):
        return "'%s'" % self.value

class HypnoBool(HypnoBasic):
    hypno_type = HYPNO_BOOL

    def render(self):
        return str(self.value)

class HypnoFunction(HypnoValue):
    hypno_type = HypnoClass('functype', base=None)

    def __init__(self, label, args, code, definition=None):
        self.fields = {}
        self.label = label
        self.args = args
        self.code = code
        self.definition = definition

    def render(self):
        return 'function<%s>' % self.label

    def is_method(self):
        return self.definition is not None

TOP_SCOPE = Env({
    'object': HYPNO_OBJECT,
    'int':    HYPNO_INT,
    'str':    HYPNO_STRING,
    'bool':   HYPNO_BOOL,
    'None':   HYPNO_NONE
}, None)

