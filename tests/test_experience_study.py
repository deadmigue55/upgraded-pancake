"""
Tests for Life Experience Study Engine
"""

import numpy as np
import pandas as pd
import pytest

from reinsurance_analytics.life.experience_study import LifeExperienceStudy


def test_garwood_poisson_ci():
    study = LifeExperienceStudy(confidence_level=0.95)
    
    # 100 actual deaths vs 100 expected deaths
    lower, upper = study.calculate_poisson_ci(actual=100, expected=100)
    assert 0.80 < lower < 0.85
    assert 1.20 < upper < 1.25

    # 0 actual deaths vs 10 expected
    low_0, high_0 = study.calculate_poisson_ci(actual=0, expected=10)
    assert low_0 == 0.0
    assert high_0 > 0.0


def test_experience_study_aggregation():
    study = LifeExperienceStudy()
    df = pd.DataFrame([
        {"age_band": "40-49", "is_death": 5, "expected_claims_count": 4.0, "exposure_years": 1000.0, "claim_amount_gross": 500000.0, "expected_claims_amount": 400000.0},
        {"age_band": "40-49", "is_death": 3, "expected_claims_count": 4.0, "exposure_years": 1000.0, "claim_amount_gross": 300000.0, "expected_claims_amount": 400000.0},
        {"age_band": "50-59", "is_death": 12, "expected_claims_count": 10.0, "exposure_years": 1500.0, "claim_amount_gross": 1200000.0, "expected_claims_amount": 1000000.0},
    ])

    result = study.analyze(
        df,
        group_cols=["age_band"],
        actual_count_col="is_death",
        expected_count_col="expected_claims_count",
        exposure_col="exposure_years",
        actual_amount_col="claim_amount_gross",
        expected_amount_col="expected_claims_amount",
    )

    assert result.total_exposure_years == 3500.0
    assert result.actual_claims_count == 20
    assert result.expected_claims_count == 18.0
    assert np.isclose(result.ae_ratio_count, 20.0 / 18.0)
    assert len(result.summary_table) == 2
