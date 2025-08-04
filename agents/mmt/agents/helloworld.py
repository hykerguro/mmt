from . import agent, FromConfig


@agent("Alice", init_args=(FromConfig("redis/host"), "114514",), init_kwargs=dict(kwarg1="1919"))
class HelloWorld:
    def __init__(self, arg1, arg2, *, kwarg1=None, kwarg2=None):
        self.arg1 = arg1
        self.arg2 = arg2
        self.kwarg1 = kwarg1
        self.kwarg2 = kwarg2

    def hello(self, there) -> str:
        return f'[{self.arg1}:{self.kwarg1}] Hello, {there}!'
