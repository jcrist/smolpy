import dis
import operator


class VM:
    def __init__(self, globals=None):
        self.f_globals = globals or {}
        self.reset()

    def reset(self):
        self.func = None
        self.f_locals = None
        self.stack = None
        self.result = None

    def top(self):
        return self.stack[-1]

    def topn(self, n):
        return self.stack[-n:]

    def pop(self, n=0):
        return self.stack.pop(-1 - n)

    def push(self, *vals):
        self.stack.extend(vals)

    def popn(self, n):
        if n:
            ret = self.stack[-n:]
            self.stack[-n:] = []
            return ret
        return []

    def next_op(self, _have_argument=dis.HAVE_ARGUMENT):
        op = self.func.co_code[self.f_lasti]
        arg = self.func.co_code[self.f_lasti + 1]
        self.f_lasti += 2
        op_name = dis.opname[op]
        return (op_name, arg) if op >= _have_argument else (op_name, None)

    def dispatch(self, op_name, arg):
        status = None
        try:
            if op_name.startswith("UNARY_"):
                self.do_unary(op_name)
            elif op_name.startswith("BINARY_"):
                self.do_binary(op_name)
            elif op_name.startswith("INPLACE_"):
                self.do_inplace(op_name)
            else:
                handler = getattr(self, f"do_{op_name}", None)
                if handler is None:
                    raise NotImplementedError("bytecode op: %s" % op_name)
                status = handler(arg) if arg is not None else handler()
        except Exception as exc:
            self.result = exc
            status = False
        return status

    def execute(self, func, *args, **kwargs):
        args = func.signature.bind(*args, **kwargs)
        args.apply_defaults()

        try:
            self.func = func
            self.f_locals = dict(args.arguments)
            self.stack = []
            self.f_lasti = 0

            while True:
                op, arg = self.next_op()
                status = self.dispatch(op, arg)
                if status is not None:
                    break

            if not status:
                raise self.result
            return self.result
        finally:
            self.reset()

    BINARY_OPS = {
        "BINARY_ADD": operator.add,
        "BINARY_AND": operator.and_,
        "BINARY_FLOOR_DIVIDE": operator.floordiv,
        "BINARY_LSHIFT": operator.lshift,
        "BINARY_MATRIX_MULTIPLY": operator.matmul,
        "BINARY_MODULO": operator.mod,
        "BINARY_MULTIPLY": operator.mul,
        "BINARY_OR": operator.or_,
        "BINARY_POWER": operator.pow,
        "BINARY_RSHIFT": operator.rshift,
        "BINARY_SUBSCR": operator.getitem,
        "BINARY_SUBTRACT": operator.sub,
        "BINARY_TRUE_DIVIDE": operator.truediv,
        "BINARY_XOR": operator.xor,
    }

    def do_binary(self, op):
        a, b = self.popn(2)
        self.push(self.BINARY_OPS[op](a, b))

    UNARY_OPS = {
        "UNARY_INVERT": operator.invert,
        "UNARY_NEGATIVE": operator.neg,
        "UNARY_NOT": operator.not_,
        "UNARY_POSITIVE": operator.pos,
    }

    def do_unary(self, op):
        a = self.pop()
        self.push(self.UNARY_OPS[op](a))

    INPLACE_OPS = {
        "INPLACE_ADD": operator.iadd,
        "INPLACE_AND": operator.iand,
        "INPLACE_FLOOR_DIVIDE": operator.ifloordiv,
        "INPLACE_LSHIFT": operator.ilshift,
        "INPLACE_MATRIX_MULTIPLY": operator.imatmul,
        "INPLACE_MODULO": operator.imod,
        "INPLACE_MULTIPLY": operator.imul,
        "INPLACE_OR": operator.ior,
        "INPLACE_POWER": operator.ipow,
        "INPLACE_RSHIFT": operator.irshift,
        "INPLACE_SUBTRACT": operator.isub,
        "INPLACE_TRUE_DIVIDE": operator.itruediv,
        "INPLACE_XOR": operator.ixor,
    }

    def do_inplace(self, op):
        a, b = self.popn(2)
        self.push(self.INPLACE_OPS[op](a, b))

    COMPARE_OPS = [
        operator.lt,
        operator.le,
        operator.eq,
        operator.ne,
        operator.gt,
        operator.ge,
        lambda a, b: a in b,
        lambda a, b: a not in b,
        operator.is_,
        operator.is_not,
    ]

    def do_COMPARE_OP(self, op):
        a, b = self.popn(2)
        self.push(self.COMPARE_OPS[op](a, b))

    def do_LOAD_CONST(self, arg):
        self.push(self.func.co_consts[arg])

    def do_LOAD_FAST(self, arg):
        name = self.func.co_varnames[arg]
        try:
            val = self.f_locals[name]
        except KeyError:
            raise UnboundLocalError(
                f"local variable {name} referenced before assignment"
            )
        self.push(val)

    def do_STORE_FAST(self, arg):
        name = self.func.co_varnames[arg]
        self.f_locals[name] = self.pop()

    def do_DELETE_FAST(self, arg):
        name = self.func.co_varnames[arg]
        del self.f_locals[name]

    def do_LOAD_GLOBAL(self, arg):
        name = self.func.co_names[arg]
        try:
            val = self.f_globals[name]
        except KeyError:
            raise NameError(f"global name {name} is not defined")
        self.push(val)

    def do_LOAD_ATTR(self, arg):
        attr = self.func.co_names[arg]
        obj = self.pop()
        self.push(getattr(obj, attr))

    def do_STORE_ATTR(self, arg):
        attr = self.func.co_names[arg]
        val, obj = self.popn(2)
        setattr(obj, attr, val)

    def do_DELETE_ATTR(self, arg):
        attr = self.func.co_names[arg]
        obj = self.pop()
        delattr(obj, attr)

    def do_STORE_SUBSCR(self):
        val, obj, key = self.popn(3)
        obj[key] = val

    def do_DELETE_SUBSCR(self):
        obj, key = self.popn(2)
        del obj[key]

    def do_POP_JUMP_IF_TRUE(self, arg):
        if self.pop():
            self.f_lasti = arg

    def do_POP_JUMP_IF_FALSE(self, arg):
        if not self.pop():
            self.f_lasti = arg

    def do_JUMP_IF_TRUE_OR_POP(self, arg):
        if self.top():
            self.f_lasti = arg
        else:
            self.pop()

    def do_JUMP_IF_FALSE_OR_POP(self, arg):
        if not self.top():
            self.f_lasti = arg
        else:
            self.pop()

    def do_JUMP_ABSOLUTE(self, arg):
        self.f_lasti = arg

    def do_JUMP_FORWARD(self, arg):
        self.f_lasti += arg

    def do_POP_TOP(self):
        self.pop()

    def do_DUP_TOP(self):
        self.push(self.top())

    def do_DUP_TOP_TWO(self):
        self.push(*self.peekn(2))

    def do_ROT_TWO(self):
        a, b = self.popn(2)
        self.push(b, a)

    def do_ROT_THREE(self):
        a, b, c = self.popn(3)
        self.push(c, a, b)

    def do_ROT_FOUR(self):
        a, b, c, d = self.popn(3)
        self.push(d, a, b, c)

    def do_GET_ITER(self):
        self.push(iter(self.pop()))

    def do_FOR_ITER(self, arg):
        iterator = self.top()
        try:
            v = next(iterator)
            self.push(v)
        except StopIteration:
            self.pop()
            self.f_lasti += arg

    def do_CALL_FUNCTION(self, arg):
        args = self.popn(arg)
        func = self.pop()
        self.push(func(*args))

    def do_RETURN_VALUE(self):
        self.result = self.pop()
        return True
