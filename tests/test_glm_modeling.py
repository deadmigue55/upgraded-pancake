"""
Tests for Actuarial GLM Modeling and Survival Analysis
"""

import numpy as np
import pandas as pd
import pytest

from reinsurance_analytics.life.glm_modeling import ActuarialGLMExperience, SurvivalExperienceAnalyzer


def test_actuarial_glm_with_offset():
    # Synthetic experience data
    rng = np.random.default_rng(42)
    n = 200
    exposures = rng.uniform(50.0, 500.0, size=n)
    is_smoker = rng.choice([0, 1], size=n, p=[0.7, 0.3])
    
    # Expected rate: 0.01 for non-smoker, 0.02 for smoker
    rates = np.where(is_smoker == 1, 0.025, 0.01)
    claims = rng.poisson(exposures * rates)

    df = pd.DataFrame({
        "claims": claims,
        "exposure": exposures,
        "smoker": is_smoker,
    })

    glm = ActuarialGLMExperience(family="poisson")
    res = glm.fit(df, formula="claims ~ C(smoker)", exposure_col="exposure")

    assert "relativities" in res
    assert res["aic"] > 0
    # Smoker relativity should be > 1.5
    smoker_rel = res["relativities"].loc["C(smoker)[T.1]", "Relativity_exp_beta"]
    assert smoker_rel > 1.5


def test_kaplan_meier_survival():
    durations = np.array([1, 2, 2, 3, 4, 5, 5, 6])
    events = np.array([0, 1, 0, 1, 0, 1, 0, 0])

    km_df = SurvivalExperienceAnalyzer.kaplan_meier(durations, events)
    assert len(km_df) > 0
    assert "survival_prob" in km_df.columns
    assert "std_err" in km_df.columns
    assert km_df.iloc[-1]["survival_prob"] < 1.0
