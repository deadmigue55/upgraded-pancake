"""
Extreme Value Theory (EVT) for Reinsurance Tail Risk
=====================================================

Implements:
- Peaks-Over-Threshold (POT) modeling with Generalized Pareto Distribution (GPD)
- Hill estimator for heavy-tail index alpha
- High-quantile return levels and Extreme Tail Value at Risk (TVaR)
"""

from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats


class ExtremeValueAnalyzer:
    """
    EVT Engine for Reinsurance High Layer Pricing and Extreme Loss Experience.
    """

    def __init__(self, data: np.ndarray):
        arr = np.asarray(data, dtype=float)
        self.data = np.sort(arr[arr > 0])[::-1]  # Descending order
        self.n = len(self.data)

    def hill_estimator(self, k: int) -> Tuple[float, float]:
        """
        Compute Hill estimator for extreme value index xi and tail index alpha = 1 / xi.
        
        Formula:
            H_{k, n} = 1/k * sum_{i=1}^k ln(X_{(i)} / X_{(k+1)})
        """
        if k < 2 or k >= self.n:
            raise ValueError(f"k must be between 2 and {self.n - 1}")

        top_k = self.data[:k]
        threshold = self.data[k]

        xi = float(np.mean(np.log(top_k / threshold)))
        alpha = float(1.0 / xi) if xi > 0 else float("inf")
        return xi, alpha

    def generate_hill_plot_data(self, min_k: int = 5, max_k: Optional[int] = None) -> pd.DataFrame:
        """Generate Hill plot data across a range of upper order statistics k."""
        max_k_val = max_k or int(self.n * 0.5)
        records = []
        for k in range(min_k, max_k_val):
            xi, alpha = self.hill_estimator(k)
            threshold = self.data[k]
            records.append({
                "k_exceedances": k,
                "threshold_u": threshold,
                "shape_xi": xi,
                "tail_index_alpha": alpha,
            })
        return pd.DataFrame(records)

    def fit_peaks_over_threshold(
        self,
        threshold: Optional[float] = None,
        quantile_threshold: float = 0.90,
    ) -> Dict[str, Any]:
        """
        Fit GPD to excesses above high threshold u:
        Y = (X - u) | X > u ~ GPD(xi, sigma)
        """
        if threshold is None:
            u = float(np.quantile(self.data, quantile_threshold))
        else:
            u = float(threshold)

        excesses = self.data[self.data > u] - u
        n_u = len(excesses)
        if n_u < 5:
            raise ValueError(f"Too few exceedances above threshold {u} (n_u={n_u})")

        # Fit GPD via MLE
        xi_hat, _, sigma_hat = stats.genpareto.fit(excesses, floc=0)

        # Fraction of exceedances
        zeta_u = n_u / self.n

        return {
            "threshold_u": u,
            "exceedance_count_nu": n_u,
            "total_observations_n": self.n,
            "exceedance_probability_zeta": zeta_u,
            "shape_xi": float(xi_hat),
            "scale_sigma": float(sigma_hat),
        }

    def predict_extreme_quantiles(
        self,
        pot_results: Dict[str, Any],
        probabilities: Tuple[float, ...] = (0.99, 0.995, 0.999),
    ) -> pd.DataFrame:
        """
        Calculate extreme Value at Risk (VaR) and Tail Value at Risk (TVaR)
        using POT formula:
            VaR_p = u + (sigma / xi) * [ ((n / n_u) * (1 - p))^(-xi) - 1 ]
            TVaR_p = (VaR_p + sigma - xi * u) / (1 - xi), for xi < 1
        """
        u = pot_results["threshold_u"]
        xi = pot_results["shape_xi"]
        sigma = pot_results["scale_sigma"]
        zeta = pot_results["exceedance_probability_zeta"]

        records = []
        for p in probabilities:
            if 1.0 - p >= zeta:
                # Inside empirical empirical body
                var_p = float(np.quantile(self.data, p))
            else:
                # POT extrapolation
                factor = ((1.0 - p) / zeta) ** (-xi) - 1.0
                if np.isclose(xi, 0.0):
                    var_p = u - sigma * np.log((1.0 - p) / zeta)
                else:
                    var_p = u + (sigma / xi) * factor

            if xi < 1.0:
                tvar_p = (var_p + sigma - xi * u) / (1.0 - xi)
            else:
                tvar_p = float("inf")  # Infinite expected shortfall for very heavy tails

            records.append({
                "Confidence_Level": p,
                "Return_Period_Years": round(1.0 / (1.0 - p), 1) if p < 1.0 else float("inf"),
                "Extreme_VaR": float(var_p),
                "Extreme_TVaR": float(tvar_p),
            })

        return pd.DataFrame(records)
