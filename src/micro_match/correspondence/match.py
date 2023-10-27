import json
import os

import numpy as np
import vedo as vp
from scipy.optimize import linear_sum_assignment

from ..tools import geometric_utilities as util
from ..tools.mesh_class import mesh_loader
from .functional_maps import functional_mapping as fm
from .functional_maps import zoom_out as zo
from .product_manifold_filters import product_manifold_filter as pmf


def readJSON(fn):
    data: dict
    with open(fn) as file:
        data = json.load(file)
    return data


def normalise(x, axis):
    x = x.copy()
    x -= x.min(axis=axis)
    x /= x.max(axis=axis)
    return x


def compute_correspondence(src, dst, config):
    C = fm.correspondenceMatrixSolver(
        src,
        dst,
        k=config["initial_solve_dimension"],
        optimise=config["symmetry_optimisation"],
    )
    C = zo.zoomout_refinement(src, dst)(C)
    P = fm.soft_correspondence(src, dst, C)
    assign = lambda x: linear_sum_assignment(x, maximize=True)
    i, j = pmf.product_manifold_filter_assignment(
        assign,
        src.g,
        dst.g,
        P,
        config["product_manifold_filter"],
    )
    return i, j


class Match:
    def __init__(self, dir_in, config, dir_out=None, display_result=False):
        self.loader = mesh_loader(dir_in)
        self.dir_out = dir_out
        self.display = display_result
        self.config = config

    def __call__(self, f1, f2):
        src = self.loader(f1, normalise=True)
        dst = self.loader(f2, normalise=True)

        fn1, fn2 = f1, f2
        if dst.num_vertices() < src.num_vertices():
            fn1, fn2 = f2, f1
            src, dst = dst, src

        fout = (
            os.path.join(self.dir_out, fn1 + "_" + fn2 + ".npy")
            if self.dir_out
            else -1
        )
        i, j = (
            np.load(fout)
            if os.path.exists(fout)
            else compute_correspondence(src, dst, self.config)
        )
        dg = np.abs(src.g[i][:, i] - dst.g[j][:, j]).mean()

        print(fn1 + " -> " + fn2 + f": geodesic distortion = {dg:.3f}")

        if self.display:
            R = util.orthogonalProcrustes(src.v[i], dst.v[j])
            dst.rotate(R)
            fig = vp.plotter.Plotter()
            fig.add([m.vedo() for m in (src, dst)])
            fig.show()
            fig.clear()

        if not fout == -1:
            np.save(fout, np.stack([i, j], axis=0))

        # Return geodesic distortion between the two objects
        return dg
