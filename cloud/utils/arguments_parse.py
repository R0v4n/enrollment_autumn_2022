import os
from argparse import ArgumentTypeError
from typing import Callable


def validate(type_: Callable, constrain: Callable):
    def wrapper(value):
        value = type_(value)
        if not constrain(value):
            raise ArgumentTypeError
        return value

    return wrapper


positive_int = validate(int, constrain=lambda x: x > 0)


def clear_environ(rule: Callable[[str], bool]):
    for name in filter(rule, tuple(os.environ)):
        os.environ.pop(name)
