"""
Implements basic rootfinding and convex optimization schemes for spherical geometry.
"""

from typing import Callable, Union
import numpy as np

default_tol = np.sqrt(np.finfo(float).eps)      # half of max precision
invgr = (np.sqrt(5) - 1) / 2                    # inverted golden ratio


def bisection(
        f: Callable[[float], float],
        a: float,
        b: float,
        atol: float = default_tol,
        fa=None,
        fb=None
) -> Union[float, None]:
    """
    Use the bisection method to estimate a root of f on the interval [a, b]. The root must exist and be unique.

    :param f: function for rootfinding
    :param a: lower bound
    :param b: upper bound
    :param atol: absolute tolerance
    :param fa: optionally f(a)
    :param fb: optionally f(b)
    :return: the approximate root, or None if no root is found
    """
    m = (a + b) / 2
    fa = fa if fa is not None else f(a)
    fb = fb if fb is not None else f(b)
    fm = f(m)
    # base case: return mid- or endpoint closest to root
    if b - a < atol:
        return [a, m, b][np.argmin(np.abs([fa, fm, fb]))]
    # recursive case: search for root on subinterval
    if fa * fm < 0:
        return bisection(f, a=a, b=m, atol=atol, fa=fa, fb=fm)
    if fm * fb <= 0:
        return bisection(f, a=m, b=b, atol=atol, fa=fm, fb=fb)


def goldensection(
        f: Callable[[float], float],
        a: float,
        b: float,
        atol: float = default_tol,
        _fx=None,
        _fy=None
) -> tuple:
    """
    Use Golden Section Search to minimize a continuous function f on the interval [a, b]. A local minimum is
    guaranteed generally; the global minimum is guaranteed if -f is unimodal.

    :param f: function to minimize
    :param a: lower bound
    :param b: upper bound
    :param atol: absolute tolerance
    :param _fx: internal use only
    :param _fy: internal use only
    :return: m, an approximate local minimizer, followed by f(m), the local minimum
    """
    # base case: return smallest of endpoints and midpoint
    if b - a < atol:
        m = (a + b) / 2
        fm = f(m)
        fa = f(a)
        fb = f(b)
        if fa < fm:
            return a, fa
        if fb < fm:
            return b, fb
        return m, fm
    # recursive case: minimize over subinterval
    x = invgr * a + (1 - invgr) * b
    y = (1 - invgr) * a + invgr * b
    fx = _fx if _fx is not None else f(x)
    fy = _fy if _fy is not None else f(y)
    if fx <= fy:
        return goldensection(f, a=a, b=y, atol=atol, _fy=fx)
    return goldensection(f, a=x, b=b, atol=atol, _fx=fy)

