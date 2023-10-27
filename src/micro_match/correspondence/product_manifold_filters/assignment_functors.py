import numpy as np
from degenerate_assignment_problem import degenerate_assignment

from ...tools import geometric_utilities as util

""" ======================================================================================================= """
"""                                        Assignment                                                       """
""" ======================================================================================================= """


class elastic_assignment_functor:
    def __init__(self, mesh, stretch):
        self.idx = mesh.decimate(frac=1 / stretch)[-1]
        self.jdx = mesh.g[self.idx].argmin(axis=0)
        self.g = mesh.g

    def reduce_scalar(self, scalar):
        shape = [self.idx.size] + list(scalar.shape)[1:]
        res = np.zeros(shape)
        np.add.at(res, self.jdx, scalar)
        return res

    def __call__(self, P):
        P = self.reduce_scalar(P.T).T
        nx, ny = (int(0.05 * s) for s in P.shape)
        fsbl = np.logical_or(
            util.first_n(-P, nx, axis=0), util.first_n(-P, ny, axis=1)
        )
        _, j = degenerate_assignment(P, feasible=fsbl)
        i = np.arange(P.shape[0])
        return i, self.idx[j]
