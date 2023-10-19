"""
Implements basic rootfinding and convex optimization schemes for spherical geometry.
"""
from typing import Callable


def bisection(
        func: Callable[[float], float],
        a: float = 0,
        b: float = 1,
        atol: float = 1e-10,
        fa=None,
        fb=None
):
    """
    Use the bisection method to estimate a root of func on the interval [a, b].

    :param func: function for rootfinding
    :param a: lower bound
    :param b: upper bound
    :param atol: absolute tolerance
    :param fa: optionally func(a)
    :param fb: optionally func(b)
    :return: the approximate root, or None if no root is on the interval
    """
    midpoint = (a + b) / 2
    if b - a < atol:
        return midpoint
    fa = fa if fa is not None else func(a)
    fb = fb if fb is not None else func(b)
    fm = func(midpoint)
    if fa * fm < 0:
        return bisection(func, a=a, b=midpoint, atol=atol, fa=fa, fb=fm)
    if fm * fb <= 0:
        return bisection(func, a=midpoint, b=b, atol=atol, fa=fm, fb=fb)
