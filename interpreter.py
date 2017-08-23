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
        self.env.base_env[label] = runtime.HypnoFunction(label, args, code)        
        return self.env['None']

    def _run_assign(self, node):
        # "Module(body=[Assign(targets=[Name(id='s', ctx=Store())], value=Num(n=2))], docstring=None)"
        # ast.parse('s = 2')
        if len(node.targets) > 1:
            raise NotImplementedError('multiple')
        value = self._run(node.value)
        self.env[node.targets[0].id] = value
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
        elif isinstance(node.func, ast.Name):
            function = self.env.base_env[node.func.id]
            # we create the function scope with args
            self.env = Env({label: self._run(value) for label, value in zip(function.args, node.args)}, parent=self.env)
            effect = [self._run(code) for code in function.code][-1]
            # we go back to scope
            self.env = self.env.parent
            return effect
        else:
            raise NotImplementedError('function')

    def _run_name(self, node):
        # "Module(body=[Expr(value=Name(id='s', ctx=Load()))], docstring=None)"
        # ast.parse('s')
        return self.env[node.id]

def program():
    with open(sys.argv[1], 'r') as f:
        python = f.read()
        Interpreter.run(ast.parse(python))

if __name__ == '__main__':
    program()
