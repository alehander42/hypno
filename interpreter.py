import ast, errors, runtime, sys
from env import Env

NATIVE = {
    'print': lambda values, env: print(*[a.render() for a in values]),
    'str':   lambda values, env: values[0].render()
}

class Interpreter:
    def __init__(self, node, env):
        self.node = node
        self.env = env
        self.definition = None
        self.this = None

    @classmethod
    def run(cls, node):
        cls(node, runtime.TOP_SCOPE)._run(node)


    def _run(self, node):
        '''
        we pass the node to a special method based on its type
        '''
        return getattr(self, '_run_%s' % type(node).__name__.lower())(node)

    def _run_module(self, node):
        # "Module(body=[Assign(targets=[Name(id='s', ctx=Store())], value=Num(n=2))], docstring=None)"
        # ast.parse('s = 2')
        for expression in node.body:
            self._run(expression)

    def _run_functiondef(self, node):
        # Module(body=[FunctionDef(name='a', args=arguments(args=[arg(arg='n', annotation=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]), body=[Assign(targets=[Name(id='s', ctx=Store())], value=Num(n=2)), Expr(value=Call(func=Name(id='print', ctx=Load()), args=[Name(id='s', ctx=Load())], keywords=[]))], decorator_list=[], returns=None, docstring=None), Expr(value=Call(func=Name(id='a', ctx=Load()), args=[Num(n=2)], keywords=[]))], docstring=None)
        # def a(b):
        #     s = b
        #     print(s)
        label = node.name
        args = [a.arg for a in node.args.args]
        code = node.body
        if self.definition is None:
            self.env.base_env[label] = runtime.HypnoFunction(label, args, code)
        else:
            self.definition.methods[label] = runtime.HypnoFunction('%s.%s' % (self.definition.label, label), args, code, definition=self.definition)
        return self.env['None']

    def _run_assign(self, node):
        # "Module(body=[Assign(targets=[Name(id='s', ctx=Store())], value=Num(n=2))], docstring=None)"
        # ast.parse('s = 2')
        if len(node.targets) > 1:
            raise NotImplementedError('multiple')
        value = self._run(node.value)
        if isinstance(node.targets[0], ast.Name):
            self.env[node.targets[0].id] = value
        elif isinstance(node.targets[0], ast.Attribute):
            attr = self._run(node.targets[0].value)
            attr.fields[node.targets[0].attr] = value
        else:
            raise NotImplementedError(type(node.targets[0]).name)
        return self.env['None']

    def _run_expr(self, node):
        # 'Module(body=[Expr(value=Num(n=2))], docstring=None)'
        # ast.parse('2')
        return self._run(node.value)

    def _run_num(self, node):
        # 'Module(body=[Expr(value=Num(n=2))], docstring=None)'
        # ast.parse('2')
        if isinstance(node.n, int):
            return runtime.HypnoInt(node.n)
        else:
            raise NotImplementedError('other')

    def _run_call(self, node):
        # "Module(body=[Expr(value=Call(func=Name(id='print', ctx=Load()), args=[Name(id='s', ctx=Load())], keywords=[]))], docstring=None)"
        # ast.parse('print(s)')
        if isinstance(node.func, ast.Name) and node.func.id in NATIVE:
            args = [self._run(a) for a in node.args]
            NATIVE[node.func.id](args, self.env)
        else:
            handler = self._run(node.func)
            if isinstance(handler, runtime.HypnoFunction):
                # we create the function scope with args
                args = {}
                if not handler.is_method():
                    args = {label: self._run(value) for label, value in zip(handler.args, node.args)}
                else:
                    args = {label: self._run(value) for label, value in zip(handler.args[1:], node.args)}
                    args['self'] = self.this
                    self.this = None
                self.env = Env(args, parent=self.env)
                effect = [self._run(code) for code in handler.code][-1]
                # we go back to scope
                self.env = self.env.parent
                return effect
            elif isinstance(handler, runtime.HypnoClass):
                # we init it
                value = runtime.HypnoValue(handler)
                if '__init__' in handler.methods:
                    args = {label: self._run(value) for label, value in zip(handler.methods['__init__'].args[1:], node.args)}
                    args['self'] = value
                    self.env = Env(args, parent=self.env)
                    for code in handler.methods['__init__'].code:
                        self._run(code)
                    self.env = self.env.parent
                return value
            else:
                raise errors.HypnoError('invalid call %s' % type(handler).name)

    def _run_name(self, node):
        # "Module(body=[Expr(value=Name(id='s', ctx=Load()))], docstring=None)"
        # ast.parse('s')
        return self.env[node.id]

    def _run_classdef(self, node):
        # Module(body=[ClassDef(name='A', bases=[], keywords=[], body=[
        #   FunctionDef(name='__init__', args=arguments(args=[arg(arg='self', annotation=None), arg(arg='b', annotation=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]), body=[Assign(targets=[Attribute(value=Name(id='self', ctx=Load()), attr='b', ctx=Store())], value=Name(id='b', ctx=Load()))], decorator_list=[], returns=None, docstring=None),
        #   FunctionDef(name='a', args=arguments(args=[arg(arg='self', annotation=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]), body=[Expr(value=Call(func=Name(id='print', ctx=Load()), args=[Attribute(value=Name(id='self', ctx=Load()), attr='b', ctx=Load())], keywords=[]))], decorator_list=[], returns=None, docstring=None)], decorator_list=[], docstring=None), Expr(value=Call(func=Attribute(value=Call(func=Name(id='A', ctx=Load()), args=[Num(n=2)], keywords=[]), attr='a', ctx=Load()), args=[], keywords=[]))], docstring=None)
        # ast.parse('''
        # class A(object):
        #     def __init__(self, b):
        #         self.b = b
        #     def a(self):
        #         print(self.b)

        label = node.name

        # we support only single inheritance
        base = None
        if len(node.bases) > 1:
            raise errors.HypnoError('many bases')
        elif len(node.bases) == 1:
            base = node.bases[0].id

        klass = runtime.HypnoClass(label, base=base, methods={})
        self.definition = klass
        # now _run_functiondef will save functions here not in scope
        for method in node.body:
            if not isinstance(method, ast.FunctionDef):
                raise NotImplementedError('class')
            self._run_functiondef(method)
        self.definition = None

        self.env.base_env[label] = klass

    def _run_attribute(self, node):
        # "Module(body=[Expr(value=Attribute(value=Name(id='A', ctx=Load()), attr='a', ctx=Load()))], docstring=None)"
        # ast.parse('A.a')
        value = self._run(node.value)
        if node.attr in value.fields:
            return value.fields[node.attr]
        elif hasattr(value, 'definition') and node.attr in value.definition.methods:
            # self.this contains self
            self.this = value
            return value.definition.methods[node.attr]
        elif node.attr in value.hypno_type.methods:
            # in A(2).a(), self.this will be the A(2)
            self.this = value
            return value.hypno_type.methods[node.attr]
        else:
            raise errors.HypnoError('invalid field')

def program():
    with open(sys.argv[1], 'r') as f:
        python = f.read()
        Interpreter.run(ast.parse(python))

if __name__ == '__main__':
    program()
