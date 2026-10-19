"""
Tests for Heavy-Tailed Loss Distributions & MLE
"""

import numpy as np
import pytest

from reinsurance_analytics.nonlife.distributions import (
    ParetoDistribution,
    LognormalDistribution,
    LossDistributionFitter,
)


def test_pareto_distribution_mle_and_lev():
    # True alpha = 2.0, xm = 1000
    rng = np.random.default_rng(42)
    u = rng.uniform(0.001, 0.999, size=2000)
    samples = 1000.0 / ((1.0 - u) ** (1.0 / 2.0))

    fitted = ParetoDistribution.fit_mle(samples, xm=1000.0)
    assert np.isclose(fitted.alpha, 2.0, atol=0.15)
    assert fitted.xm == 1000.0

    # LEV(5000) for Pareto: E[min(X, 5000)]
    lev = fitted.limited_expected_value(5000.0)
    assert 1000.0 < lev < 2000.0


def test_lognormal_distribution_lev():
    lognorm = LognormalDistribution(mu=10.0, sigma=1.0)
    lev_100k = lognorm.limited_expected_value(100000.0)
    assert lev_100k > 0.0


def test_loss_distribution_fitter():
    rng = np.random.default_rng(101)
    data = rng.lognormal(mean=9.5, sigma=0.8, size=300)
    fitter = LossDistributionFitter(data)
    summary = fitter.fit_all()
    assert len(summary) >= 3
    best_name, best_dist = fitter.get_best_model()
    assert best_name in ["Lognormal", "Weibull", "Pareto", "GPD_Tail"]
