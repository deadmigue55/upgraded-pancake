"""
Tests for Actuarial Exposure Engine
"""

import pandas as pd
import numpy as np
import pytest

from reinsurance_analytics.core.exposure import ExposureEngine, ExposureMethod


def test_continuous_exposure_calculation():
    engine = ExposureEngine(study_start="2020-01-01", study_end="2020-12-31")
    
    # Policy active full study year
    exp = engine.calculate_policy_exposure(
        issue_date=pd.Timestamp("2019-01-01"),
        exit_date=None,
    )
    # Days in 2020: 366 (leap year). 366 / 365.25 ~ 1.002
    assert 0.99 < exp < 1.01


def test_exposure_portfolio_processing():
    engine = ExposureEngine(study_start="2020-01-01", study_end="2022-12-31")
    
    df = pd.DataFrame([
        {
            "policy_id": "P1",
            "issue_date": "2020-01-01",
            "exit_date": "2021-01-01",
            "status": "LAPSE",
            "face_amount": 100000.0,
            "retention_limit": 50000.0,
        },
        {
            "policy_id": "P2",
            "issue_date": "2021-01-01",
            "exit_date": None,
            "status": "ACTIVE",
            "face_amount": 200000.0,
            "retention_limit": 50000.0,
        },
        {
            "policy_id": "P3",
            "issue_date": "2019-01-01",
            "exit_date": "2021-07-01",
            "status": "DEATH",
            "face_amount": 500000.0,
            "retention_limit": 100000.0,
        },
    ])

    processed = engine.process_portfolio(df)
    assert len(processed) == 3
    assert "exposure_years" in processed.columns
    assert "ceded_exposure" in processed.columns
    assert "claim_amount_ceded" in processed.columns

    # P3 died: Gross claim = 500k, Retained = 100k, Ceded = 400k
    p3 = processed[processed["policy_id"] == "P3"].iloc[0]
    assert p3["is_death"] == 1
    assert p3["claim_amount_gross"] == 500000.0
    assert p3["claim_amount_ceded"] == 400000.0
    assert p3["retained_amount"] == 100000.0
