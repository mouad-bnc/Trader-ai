from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import streamlit as st

P = ParamSpec("P")
T = TypeVar("T")


def cached_data(ttl: int = 300) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        cached = st.cache_data(ttl=ttl, show_spinner=False)(func)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return cached(*args, **kwargs)

        return wrapper

    return decorator
