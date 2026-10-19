"""
Tests for Reinsurance Treaty Structures and Layering
"""

import numpy as np
import pytest

from reinsurance_analytics.treaty.structures import (
    QuotaShareTreaty,
    SurplusTreaty,
    ExcessOfLossTreaty,
    ReinsuranceProgram,
)
from reinsurance_analytics.treaty.reinstatements import ReinstatementClause, ReinstatementType


def test_quota_share_treaty():
    qs = QuotaShareTreaty(cession_rate=0.40, ceding_commission=0.25)
    losses = np.array([100000.0, 500000.0])
    ceded = qs.evaluate_loss(losses)
    assert np.allclose(ceded, [40000.0, 200000.0])

    cashflows = qs.evaluate_treaty_cashflow(gross_premium=1000000.0, gross_losses=600000.0)
    assert cashflows["ceded_premium"] == 400000.0
    assert cashflows["ceding_commission"] == 100000.0
    assert cashflows["ceded_losses"] == 240000.0
    assert cashflows["reinsurer_underwriting_profit"] == 60000.0


def test_excess_of_loss_layering():
    # 2M xs 1M layer
    xl = ExcessOfLossTreaty(attachment=1000000.0, limit=2000000.0)
    
    # 500k loss -> 0 ceded
    assert xl.evaluate_loss(500000.0) == 0.0
    
    # 2M loss -> 1M ceded
    assert xl.evaluate_loss(2000000.0) == 1000000.0
    
    # 5M loss -> capped at limit 2M
    assert xl.evaluate_loss(5000000.0) == 2000000.0


def test_reinstatement_premium_calculation():
    clause = ReinstatementClause(count=1, rate=1.0, reinstatement_type=ReinstatementType.PRO_RATA_AMOUNT)
    prem = clause.calculate_reinstatement_premium(
        claim_ceded=500000.0,
        layer_limit=1000000.0,
        initial_premium=80000.0,
    )
    # 50% consumed * 100% rate * 80k = 40k
    assert prem == 40000.0
