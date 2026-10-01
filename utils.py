"""Reusable utilities for the console application."""

import inspect
from collections.abc import Callable


def describe_function(function: Callable[..., object]) -> str:
    """Return a compact introspection description of a function."""
    signature = inspect.signature(function)
    return f"{function.__name__}{signature}"
