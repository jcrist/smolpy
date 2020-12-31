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

    def next_op(self):
        op = self.func.co_code[self.f_lasti]
        self.f_lasti += 1
        # XXX: this is wrong
        int_arg = self.func.co_code[self.f_lasti]
        self.f_lasti += 1

        op_name = dis.opname[op]
        if op >= dis.HAVE_ARGUMENT:
            if op in dis.hasconst:
                arg = self.func.co_consts[int_arg]
            elif op in dis.hasname:
                arg = self.func.co_names[int_arg]
            elif op in dis.haslocal:
                arg = self.func.co_varnames[int_arg]
            elif op in dis.hasjrel:
                arg = self.f_lasti + int_arg
            elif op in dis.hasjabs:
                arg = int_arg
            else:
                arg = int_arg
            arguments = [arg]
        else:
            arguments = []
        return op_name, arguments

    def dispatch(self, op_name, args):
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
                status = handler(*args)
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
                op, args = self.next_op()
                status = self.dispatch(op, args)
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

    def do_LOAD_FAST(self, name):
        try:
            val = self.f_locals[name]
        except KeyError:
            raise UnboundLocalError(
                f"local variable {name} referenced before assignment"
            )
        self.push(val)

    def do_LOAD_CONST(self, const):
        self.push(const)

    def do_RETURN_VALUE(self):
        self.result = self.pop()
        return True
