import inspect


def translate(func):
    # TODO
    code = func.__code__
    return code.co_code, code.co_consts, code.co_varnames, code.co_names


class Function:
    def __init__(self, name, signature, co_code, co_consts, co_varnames, co_names):
        self.name = name
        self.signature = signature
        self.co_code = co_code
        self.co_consts = co_consts
        self.co_varnames = co_varnames
        self.co_names = co_names

    @classmethod
    def from_callable(cls, func):
        sig = inspect.signature(func)
        code, consts, varnames, names = translate(func)
        return cls(func.__qualname__, sig, code, consts, varnames, names)
