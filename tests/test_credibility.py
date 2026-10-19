"""
Tests for Actuarial Credibility Theory
"""

import numpy as np
import pandas as pd
import pytest

from reinsurance_analytics.core.credibility import (
    LimitedFluctuationCredibility,
    BuhlmannStraubCredibility,
)


def test_limited_fluctuation_poisson_standard():
    # 90% confidence, 5% margin of error: standard actuarial benchmark ~ 1082 claims
    cred = LimitedFluctuationCredibility(confidence_level=0.90, error_margin=0.05)
    n_star = cred.calculate_full_credibility_standard()
    assert np.isclose(n_star, 1082.41, atol=1.0)

    # Test full credibility condition
    res_full = cred.evaluate(observed_value=1.15, prior_mean=1.00, observed_count=1083)
    assert res_full.is_fully_credible is True
    assert res_full.credibility_factor == 1.0
    assert np.isclose(res_full.credibility_weighted_estimate, 1.15)

    # Test 50% partial credibility: n = n* / 4 => Z = 0.50
    res_half = cred.evaluate(observed_value=1.20, prior_mean=1.00, observed_count=1082.41 / 4.0)
    assert np.isclose(res_half.credibility_factor, 0.50, atol=0.01)
    assert np.isclose(res_half.credibility_weighted_estimate, 1.10, atol=0.01)


def test_buhlmann_straub_credibility():
    # Synthetic panel data for 3 cedants over 4 years
    data = [
        {"cedant": "C1", "year": 1, "loss_ratio": 0.65, "exposure": 1000},
        {"cedant": "C1", "year": 2, "loss_ratio": 0.60, "exposure": 1100},
        {"cedant": "C1", "year": 3, "loss_ratio": 0.70, "exposure": 1050},
        {"cedant": "C2", "year": 1, "loss_ratio": 0.85, "exposure": 800},
        {"cedant": "C2", "year": 2, "loss_ratio": 0.80, "exposure": 850},
        {"cedant": "C2", "year": 3, "loss_ratio": 0.90, "exposure": 900},
        {"cedant": "C3", "year": 1, "loss_ratio": 0.50, "exposure": 1500},
        {"cedant": "C3", "year": 2, "loss_ratio": 0.55, "exposure": 1600},
        {"cedant": "C3", "year": 3, "loss_ratio": 0.48, "exposure": 1550},
    ]
    df = pd.DataFrame(data)
    bs = BuhlmannStraubCredibility()
    params = bs.fit(df, group_col="cedant", loss_ratio_col="loss_ratio", exposure_col="exposure")

    assert params["epv_s2"] > 0
    assert params["vhm_a"] > 0
    assert params["buhlmann_constant_k"] > 0
    assert 0.50 < params["collective_mean_mu"] < 0.80

    pred_c1 = bs.predict_group(exposure=3150, observed_mean=0.65)
    assert 0.0 < pred_c1.credibility_factor < 1.0
