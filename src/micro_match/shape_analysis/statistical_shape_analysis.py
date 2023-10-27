import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from sklearn.decomposition import PCA

from ..tools import geometric_utilities as util


def centre(x, axis):
    x -= x.mean(axis=axis, keepdims=True)
    return x


def normalise(x, axis):
    x /= np.linalg.norm(x, axis=axis, keepdims=True)
    return x


def collection_deviation(point_clouds, iterations=15):
    centre(point_clouds, axis=1)
    normalise(point_clouds, axis=(1, 2))
    template = np.mean(point_clouds, axis=0)
    for _ in range(iterations):
        normalise(template, axis=None)
        y = []
        for x in point_clouds:
            R = util.orthogonalProcrustes(template, x)
            y.append(x @ R)
        point_clouds = np.stack(y, axis=0)
        template = np.mean(point_clouds, axis=0)
    return point_clouds - template


def clustering_analysis(classes, deviations, variant):
    classes = np.asarray(classes)
    unique = np.unique(classes)
    cmap = cm.get_cmap("Set1")

    dp = deviations.reshape(deviations.shape[0], -1)
    pca = PCA(n_components=2, svd_solver="full")
    S = pca.fit_transform(dp)

    fig, ax = plt.subplots()

    for c, var in zip(cmap.colors, unique):
        x, y = S[classes == var].T
        ax.scatter(x, y, c=c, s=250)

    ax.set_title(variant, fontsize=32)
    ax.legend(labels=unique, fontsize=16)
    plt.show()
