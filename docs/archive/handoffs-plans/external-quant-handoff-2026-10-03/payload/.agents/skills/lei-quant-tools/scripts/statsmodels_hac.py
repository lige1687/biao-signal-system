# Selected unchanged functions from statsmodels 0.15.0.
# Copyright (c) 2009-2018 statsmodels Developers and other copyright holders.
# BSD-3-Clause; full notice in statsmodels-LICENSE.txt.
# Authors: Josef Perktold and Skipper Seabold (upstream file attribution).
# Source: statsmodels/stats/sandwich_covariance.py from the pinned PyPI wheel.
# Packaging change only: select two original functions and import numpy.
import numpy as np


def weights_bartlett(nlags):
    """
    Bartlett weights for HAC

    this will be moved to another module

    Parameters
    ----------
    nlags : int
       highest lag in the kernel window, this does not include the zero lag

    Returns
    -------
    kernel : ndarray, (nlags+1,)
        weights for Bartlett kernel

    """

    # with lag zero

    return 1 - np.arange(nlags + 1) / (nlags + 1.0)


def S_hac_simple(x, nlags=None, weights_func=weights_bartlett):
    """
    Inner covariance matrix for HAC (Newey, West) sandwich

    assumes we have a single time series with zero axis consecutive, equal
    spaced time periods

    Parameters
    ----------
    x : ndarray (nobs,) or (nobs, k_var)
        data, for HAC this is array of x_i * u_i
    nlags : int or None, optional
        highest lag to include in kernel window. If None, then
        nlags = floor(4(T/100)^(2/9)) is used.
    weights_func : callable, optional
        weights_func is called with nlags as argument to get the kernel
        weights. default are Bartlett weights

    Returns
    -------
    S : ndarray, (k_vars, k_vars)
        inner covariance matrix for sandwich

    Notes
    -----
    used by cov_hac_simple

    options might change when other kernels besides Bartlett are available.

    """

    if x.ndim == 1:
        x = x[:, None]
    n_periods = x.shape[0]
    if nlags is None:
        nlags = int(np.floor(4 * (n_periods / 100.0) ** (2.0 / 9.0)))
    weights = weights_func(nlags)

    S = weights[0] * np.dot(x.T, x)  # weights[0] just for completeness, is 1

    for lag in range(1, nlags + 1):
        s = np.dot(x[lag:].T, x[:-lag])
        S += weights[lag] * (s + s.T)
    return S
