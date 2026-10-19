"""
Actuarial Risk Metrics & Capital Relief Analysis
=================================================

Computes:
- Value at Risk (VaR_alpha)
- Tail Value at Risk (TVaR_alpha / Expected Shortfall / CTE)
- Solvency II / RBC 1-in-200 year (99.5%) Capital Relief
- Aggregate and Occurrence Exceedance Probabilities (AEP / OEP)
- Reinsurance underwriting efficiency & Return on Risk Capital
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd


@dataclass
class CapitalReliefSummary:
    """Solvency II / RBC Capital Relief comparison."""
    gross_expected_loss: float
    net_expected_loss: float
    ceded_expected_loss: float
    gross_var_995: float
    net_var_995: float
    ceded_var_995: float
    gross_tvar_995: float
    net_tvar_995: float
    ceded_tvar_995: float
    gross_required_capital: float
    net_required_capital: float
    capital_relief_amount: float
    capital_relief_percentage: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_expected_loss": round(self.gross_expected_loss, 2),
            "net_expected_loss": round(self.net_expected_loss, 2),
            "ceded_expected_loss": round(self.ceded_expected_loss, 2),
            "gross_var_995": round(self.gross_var_995, 2),
            "net_var_995": round(self.net_var_995, 2),
            "ceded_var_995": round(self.ceded_var_995, 2),
            "gross_tvar_995": round(self.gross_tvar_995, 2),
            "net_tvar_995": round(self.net_tvar_995, 2),
            "ceded_tvar_995": round(self.ceded_tvar_995, 2),
            "gross_required_capital_995": round(self.gross_required_capital, 2),
            "net_required_capital_995": round(self.net_required_capital, 2),
            "capital_relief_amount": round(self.capital_relief_amount, 2),
            "capital_relief_percentage": round(self.capital_relief_percentage, 2),
        }


class ActuarialRiskMetrics:
    """
    Computes standard solvency, economic capital, and reinsurance risk metrics.
    """

    @staticmethod
    def value_at_risk(losses: np.ndarray, alpha: float = 0.995) -> float:
        """Calculate VaR at confidence level alpha."""
        arr = np.asarray(losses, dtype=float)
        return float(np.percentile(arr, alpha * 100.0))

    @staticmethod
    def tail_value_at_risk(losses: np.ndarray, alpha: float = 0.995) -> float:
        """
        Calculate Tail Value at Risk (TVaR / CTE / Expected Shortfall):
        E[Loss | Loss > VaR_alpha]
        """
        arr = np.asarray(losses, dtype=float)
        var_val = np.percentile(arr, alpha * 100.0)
        tail = arr[arr > var_val]
        if len(tail) == 0:
            return float(var_val)
        return float(np.mean(tail))

    @classmethod
    def evaluate_risk_profile(
        cls,
        losses: np.ndarray,
        quantiles: Tuple[float, ...] = (0.90, 0.95, 0.99, 0.995, 0.999),
    ) -> pd.DataFrame:
        """Tabulate VaR and TVaR across multiple return periods."""
        arr = np.asarray(losses, dtype=float)
        records = []
        for q in quantiles:
            var_val = cls.value_at_risk(arr, q)
            tvar_val = cls.tail_value_at_risk(arr, q)
            return_period = 1.0 / (1.0 - q) if q < 1.0 else float("inf")
            records.append({
                "Confidence_Level": q,
                "Return_Period_1_in_X": round(return_period, 1),
                "VaR": var_val,
                "TVaR": tvar_val,
            })
        return pd.DataFrame(records)

    @classmethod
    def calculate_capital_relief(
        cls,
        gross_losses: np.ndarray,
        net_losses: np.ndarray,
        alpha: float = 0.995,
    ) -> CapitalReliefSummary:
        """
        Solvency II 1-in-200 year SCR Capital Relief:
        SCR = VaR_{0.995}(Loss) - E[Loss]
        Capital Relief = Gross SCR - Net SCR
        """
        gross = np.asarray(gross_losses, dtype=float)
        net = np.asarray(net_losses, dtype=float)
        ceded = gross - net

        g_mean = float(np.mean(gross))
        n_mean = float(np.mean(net))
        c_mean = float(np.mean(ceded))

        g_var = cls.value_at_risk(gross, alpha)
        n_var = cls.value_at_risk(net, alpha)
        c_var = cls.value_at_risk(ceded, alpha)

        g_tvar = cls.tail_value_at_risk(gross, alpha)
        n_tvar = cls.tail_value_at_risk(net, alpha)
        c_tvar = cls.tail_value_at_risk(ceded, alpha)

        g_req_cap = max(0.0, g_var - g_mean)
        n_req_cap = max(0.0, n_var - n_mean)

        relief_amt = max(0.0, g_req_cap - n_req_cap)
        relief_pct = (relief_amt / g_req_cap * 100.0) if g_req_cap > 0 else 0.0

        return CapitalReliefSummary(
            gross_expected_loss=g_mean,
            net_expected_loss=n_mean,
            ceded_expected_loss=c_mean,
            gross_var_995=g_var,
            net_var_995=n_var,
            ceded_var_995=c_var,
            gross_tvar_995=g_tvar,
            net_tvar_995=n_tvar,
            ceded_tvar_995=c_tvar,
            gross_required_capital=g_req_cap,
            net_required_capital=n_req_cap,
            capital_relief_amount=relief_amt,
            capital_relief_percentage=relief_pct,
        )

    @staticmethod
    def generate_exceedance_curve(losses: np.ndarray, num_points: int = 100) -> pd.DataFrame:
        """
        Generate Aggregate Exceedance Probability (AEP) curve: P(Loss > x).
        """
        arr = np.sort(np.asarray(losses, dtype=float))
        n = len(arr)
        # Exceedance probabilities: 1 - i / (n + 1)
        ranks = np.arange(1, n + 1)
        exceed_prob = 1.0 - (ranks / (n + 1.0))

        # Subsample for plotting
        indices = np.linspace(0, n - 1, num=min(num_points, n), dtype=int)
        return pd.DataFrame({
            "Loss": arr[indices],
            "Exceedance_Probability": exceed_prob[indices],
            "Return_Period_Years": 1.0 / np.clip(exceed_prob[indices], 1e-6, 1.0),
        })
