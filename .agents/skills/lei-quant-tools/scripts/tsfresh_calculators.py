# Selected unchanged function bodies from tsfresh 0.21.2.
# Copyright (c) 2016 Maximilian Christ, Blue Yonder GmbH.
# MIT; full notice in tsfresh-LICENSE.txt.
# Source: tsfresh/feature_extraction/feature_calculators.py in the pinned PyPI wheel.
# Packaging only: select two functions, omit metadata decorators, import numpy/pandas.
import numpy as np
import pandas as pd


def mean_abs_change(x):
    """
    Average over first differences.

    Returns the mean over the absolute differences between subsequent time series values which is

    .. math::

        \\frac{1}{n-1} \\sum_{i=1,\\ldots, n-1} | x_{i+1} - x_{i}|


    :param x: the time series to calculate the feature of
    :type x: numpy.ndarray
    :return: the value of this feature
    :return type: float
    """
    return np.mean(np.abs(np.diff(x)))


def autocorrelation(x, lag):
    """
    Calculates the autocorrelation of the specified lag, according to the formula [1]

    .. math::

        \\frac{1}{(n-l)\\sigma^{2}} \\sum_{t=1}^{n-l}(X_{t}-\\mu )(X_{t+l}-\\mu)

    where :math:`n` is the length of the time series :math:`X_i`, :math:`\\sigma^2` its variance and :math:`\\mu` its
    mean. `l` denotes the lag.

    .. rubric:: References

    [1] https://en.wikipedia.org/wiki/Autocorrelation#Estimation

    :param x: the time series to calculate the feature of
    :type x: numpy.ndarray
    :param lag: the lag
    :type lag: int
    :return: the value of this feature
    :return type: float
    """
    # This is important: If a series is passed, the product below is calculated
    # based on the index, which corresponds to squaring the series.
    if isinstance(x, pd.Series):
        x = x.values
    if len(x) < lag:
        return np.nan
    # Slice the relevant subseries based on the lag
    y1 = x[: (len(x) - lag)]
    y2 = x[lag:]
    # Subtract the mean of the whole series x
    x_mean = np.mean(x)
    # The result is sometimes referred to as "covariation"
    sum_product = np.sum((y1 - x_mean) * (y2 - x_mean))
    # Return the normalized unbiased covariance
    v = np.var(x)
    if np.isclose(v, 0):
        return np.nan

    return sum_product / ((len(x) - lag) * v)
