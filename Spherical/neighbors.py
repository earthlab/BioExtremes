"""
Uses sklearn.neighbors.BallTree to allow nearest-neighbor queries for sets.
"""

from typing import Callable
from sklearn.neighbors import BallTree

from Spherical import numerics


class _TouchSet:
    """Determine whether a BallTree touches an arbitrary set."""

    def __init__(self, d2set: Callable, tree: BallTree, atol: float):
        self.data, self.index, self.nodes, _ = tree.get_arrays()
        self.d2set = d2set
        self.atol = atol
        self.touch, self.x = self.subtreetouch(0)

    def subtreetouch(self, root: int) -> tuple:
        """Determine whether a subtree touches the set."""
        istart, iend, isleaf, rad = self.nodes[root]
        rep = self.data[self.index[istart]]
        # base case 1: reject if this subtree is bounded away from the set
        d = self.d2set(rep)
        if d > 2 * rad + self.atol:
            return False, rep
        # base case 2: minimize over leaf by brute force
        if isleaf:
            for x in self.data[self.index[istart:iend]]:
                if self.d2set(x) < self.atol:
                    return True, x
            return False, x
        # recursive case: evaluate children
        left = 2 * root + 1
        touch, x = self.subtreetouch(left)
        if touch:
            return touch, x
        right = 2 * root + 2
        return self.subtreetouch(right)


def touchset(d2set: Callable, tree: BallTree, atol: float = numerics.default_tol) -> tuple:
    """
    Determine whether a BallTree touches an arbitrary set.

    :param d2set: Calculates distance between a point and the set. Must satisfy triangle inequality
                    d2set(x) <= d(x, y) + d2set(y) for all points y.
    :param tree: The BallTree instance.
    :param atol: Returns true if d2set(x) < atol for any x in the tree.
    :return: boolean value touch, then x, which is a touching point in the tree if touch == True. If touch == False,
                then x should be ignored.
    """
    ts = _TouchSet(d2set, tree, atol)
    return ts.touch, ts.x
