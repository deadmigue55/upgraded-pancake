"""
Tests for Collective Risk Simulation and Actuarial Risk Metrics
"""

import numpy as np
import pytest

from reinsurance_analytics.nonlife.distributions import ParetoDistribution, LognormalDistribution
from reinsurance_analytics.simulation.collective_risk import CollectiveRiskSimulator, PanjerRecursion
from reinsurance_analytics.simulation.risk_metrics import ActuarialRiskMetrics
from reinsurance_analytics.treaty.structures import ExcessOfLossTreaty, ReinsuranceProgram


def test_collective_risk_simulation():
    sev = LognormalDistribution(mu=10.0, sigma=0.8)
    sim = CollectiveRiskSimulator(severity_dist=sev, frequency_type="poisson", poisson_lambda=15.0, random_state=42)
    
    prog = ReinsuranceProgram([
        ExcessOfLossTreaty(attachment=50000.0, limit=200000.0, name="Working_XL")
    ])

    results = sim.simulate(num_trials=500, treaty_program=prog)
    assert len(results.gross_aggregate_losses) == 500
    assert len(results.net_aggregate_losses) == 500
    assert np.all(results.gross_aggregate_losses >= results.net_aggregate_losses)


def test_actuarial_risk_metrics():
    # Synthetic losses
    rng = np.random.default_rng(42)
    losses = rng.exponential(scale=100000.0, size=10000)

    var_95 = ActuarialRiskMetrics.value_at_risk(losses, alpha=0.95)
    tvar_95 = ActuarialRiskMetrics.tail_value_at_risk(losses, alpha=0.95)

    # For any continuous loss distribution, TVaR > VaR
    assert tvar_95 > var_95

    # Capital relief
    net_losses = losses * 0.70  # 30% quota share
    relief = ActuarialRiskMetrics.calculate_capital_relief(losses, net_losses, alpha=0.995)
    assert relief.capital_relief_amount > 0.0
    assert np.isclose(relief.capital_relief_percentage, 30.0, atol=2.0)


def test_panjer_recursion():
    # Discretized severity: [0.0, 0.5, 0.3, 0.2]
    f = np.array([0.0, 0.5, 0.3, 0.2])
    g = PanjerRecursion.compute(frequency_type="poisson", freq_param=2.0, severity_discretized=f, max_aggregate_units=50)
    assert len(g) == 50
    assert np.isclose(np.sum(g), 1.0, atol=0.01)
