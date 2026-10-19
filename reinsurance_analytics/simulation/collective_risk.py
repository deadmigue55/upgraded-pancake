"""
Collective Risk Modeling & Aggregate Loss Simulation
=====================================================

Implements:
1. Monte Carlo Collective Risk Simulation (Frequency-Severity compound process):
   S = sum_{i=1}^N X_i
   Evaluates Gross, Ceded (per layer), and Retained aggregate losses.
2. Panjer Recursion algorithm for exact analytical aggregate loss distributions.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from reinsurance_analytics.nonlife.distributions import ActuarialDistribution
from reinsurance_analytics.treaty.structures import ExcessOfLossTreaty, QuotaShareTreaty, ReinsuranceProgram


@dataclass
class SimulationResults:
    """Simulation output container with Gross, Ceded, and Net loss arrays."""
    gross_aggregate_losses: np.ndarray
    net_aggregate_losses: np.ndarray
    ceded_aggregate_losses: np.ndarray
    layer_ceded_losses: Dict[str, np.ndarray]
    frequency_simulated: np.ndarray
    num_trials: int

    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame({
            "Trial": np.arange(1, self.num_trials + 1),
            "Claim_Count_N": self.frequency_simulated,
            "Gross_Loss_S": self.gross_aggregate_losses,
            "Ceded_Loss": self.ceded_aggregate_losses,
            "Net_Retained_Loss": self.net_aggregate_losses,
        })
        for lyr_name, arr in self.layer_ceded_losses.items():
            df[f"Ceded_{lyr_name}"] = arr
        return df


class CollectiveRiskSimulator:
    """
    Monte Carlo Collective Risk Simulation Engine.
    
    Generates joint realizations of frequency N and severities X_1, ..., X_N
    and routes them through reinsurance treaty structures.
    """

    def __init__(
        self,
        severity_dist: ActuarialDistribution,
        frequency_type: str = "poisson",
        poisson_lambda: float = 20.0,
        negbin_r: Optional[float] = None,
        negbin_p: Optional[float] = None,
        random_state: Optional[int] = 42,
    ):
        self.severity_dist = severity_dist
        self.frequency_type = frequency_type.lower()
        self.poisson_lambda = poisson_lambda
        self.negbin_r = negbin_r
        self.negbin_p = negbin_p
        self.random_state = random_state
        self.rng = np.random.default_rng(random_state)

    def sample_frequency(self, num_trials: int) -> np.ndarray:
        """Draw sample of claim counts N for each trial year."""
        if self.frequency_type in ("negative_binomial", "negbin", "nb"):
            if self.negbin_r is None or self.negbin_p is None:
                raise ValueError("negbin_r and negbin_p must be set for Negative Binomial frequency")
            return self.rng.negative_binomial(self.negbin_r, self.negbin_p, size=num_trials)
        else:
            return self.rng.poisson(self.poisson_lambda, size=num_trials)

    def simulate(
        self,
        num_trials: int = 10000,
        treaty_program: Optional[ReinsuranceProgram] = None,
    ) -> SimulationResults:
        """
        Run stochastic Monte Carlo aggregate loss simulation.
        """
        n_samples = self.sample_frequency(num_trials)
        total_claims = int(np.sum(n_samples))

        # Vectorized severity draws
        if total_claims > 0:
            severities = self.severity_dist.rvs(total_claims, random_state=self.rng.integers(0, 1000000))
        else:
            severities = np.array([])

        # Partition severities by trial
        gross_agg = np.zeros(num_trials, dtype=float)
        net_agg = np.zeros(num_trials, dtype=float)
        ceded_agg = np.zeros(num_trials, dtype=float)

        layer_names = [getattr(l, "name", f"Layer_{i+1}") for i, l in enumerate(treaty_program.layers)] if treaty_program else []
        layer_ceded_map: Dict[str, np.ndarray] = {name: np.zeros(num_trials, dtype=float) for name in layer_names}

        curr_idx = 0
        for i in range(num_trials):
            cnt = n_samples[i]
            if cnt == 0:
                continue

            trial_losses = severities[curr_idx:curr_idx + cnt]
            curr_idx += cnt

            gross_s = float(np.sum(trial_losses))
            gross_agg[i] = gross_s

            if treaty_program is not None and len(treaty_program.layers) > 0:
                trial_res = treaty_program.evaluate(trial_losses)
                trial_total_ceded = float(trial_res["Total_Ceded"].sum())
                ceded_agg[i] = trial_total_ceded
                net_agg[i] = gross_s - trial_total_ceded

                for lyr in treaty_program.layers:
                    lyr_col = f"Ceded_{lyr.name}"
                    layer_ceded_map[lyr.name][i] = float(trial_res[lyr_col].sum())
            else:
                net_agg[i] = gross_s
                ceded_agg[i] = 0.0

        return SimulationResults(
            gross_aggregate_losses=gross_agg,
            net_aggregate_losses=net_agg,
            ceded_aggregate_losses=ceded_agg,
            layer_ceded_losses=layer_ceded_map,
            frequency_simulated=n_samples,
            num_trials=num_trials,
        )


class PanjerRecursion:
    """
    Panjer's Algorithm for Compound Aggregate Loss Distributions.
    
    Applicable to frequency distributions in the (a, b, 0) family:
    p_k = (a + b / k) * p_{k-1}
    
    For Poisson(lambda): a = 0, b = lambda
    For Negative Binomial(r, p): a = 1 - p, b = (r - 1)(1 - p)
    
    Recursion formula:
        g_0 = P_N(f_0)
        g_k = 1 / (1 - a * f_0) * sum_{j=1}^k (a + b * j / k) * f_j * g_{k-j}
    """

    @staticmethod
    def compute(
        frequency_type: str,
        freq_param: float,  # lambda for Poisson
        severity_discretized: np.ndarray,
        max_aggregate_units: int = 1000,
    ) -> np.ndarray:
        """
        Execute Panjer recursion on discretized severity PMF f_0, f_1, ..., f_m.
        """
        f = np.asarray(severity_discretized, dtype=float)
        # Ensure severity PMF sums to 1
        f = f / np.sum(f)
        f0 = f[0] if len(f) > 0 else 0.0
        m = len(f)

        if frequency_type.lower() == "poisson":
            lam = float(freq_param)
            a = 0.0
            b = lam
            g0 = np.exp(-lam * (1.0 - f0))
        else:
            raise NotImplementedError("Currently supports 'poisson' in Panjer recursion")

        g = np.zeros(max_aggregate_units, dtype=float)
        g[0] = g0

        denom = 1.0 - a * f0

        for k in range(1, max_aggregate_units):
            upper_j = min(k, m - 1)
            total = 0.0
            for j in range(1, upper_j + 1):
                coef = a + (b * j) / k
                total += coef * f[j] * g[k - j]
            g[k] = total / denom

        # Normalize in case of truncation tail
        sum_g = np.sum(g)
        if sum_g > 0:
            g = g / sum_g

        return g
