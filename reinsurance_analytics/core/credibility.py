"""
Actuarial Credibility Theory Module
====================================

Implements:
1. Limited Fluctuation Credibility (Classical / American Credibility)
2. Bühlmann-Straub Credibility (Empirical Bayes Credibility)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class CredibilityResult:
    """Actuarial credibility evaluation output."""
    credibility_factor: float
    observed_statistic: float
    prior_mean: float
    credibility_weighted_estimate: float
    full_credibility_standard: float
    sample_size: float
    variance_components: Optional[Dict[str, float]] = None
    is_fully_credible: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "credibility_factor_Z": round(self.credibility_factor, 4),
            "observed_statistic": round(self.observed_statistic, 6),
            "prior_mean": round(self.prior_mean, 6),
            "credibility_weighted_estimate": round(self.credibility_weighted_estimate, 6),
            "full_credibility_standard": round(self.full_credibility_standard, 2),
            "sample_size": round(self.sample_size, 2),
            "is_fully_credible": self.is_fully_credible,
            "variance_components": self.variance_components or {},
        }


class LimitedFluctuationCredibility:
    """
    Classical / American Limited Fluctuation Credibility.
    
    Determines credibility factor Z such that actual experience is within
    margin of error k of expected value with probability p (confidence level).
    
    Formula:
        Z = min(1.0, sqrt(n / n*))
        n* = (z_{1 - alpha/2} / k)^2 * (1 + CV^2)
    """

    def __init__(
        self,
        confidence_level: float = 0.90,  # Typically 90% (p = 0.90) or 95%
        error_margin: float = 0.05,       # Typically 5% (k = 0.05)
    ):
        if not (0.50 < confidence_level < 1.0):
            raise ValueError("confidence_level must be between 0.50 and 1.0")
        if error_margin <= 0.0:
            raise ValueError("error_margin must be positive")

        self.confidence_level = confidence_level
        self.error_margin = error_margin
        
        # Calculate normal critical value z_{1 - alpha/2}
        alpha = 1.0 - confidence_level
        self.z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
        
        # Standard full credibility claims for pure Poisson counts
        self.base_full_cred_count = (self.z_crit / self.error_margin) ** 2

    def calculate_full_credibility_standard(
        self,
        claim_amounts: Optional[Union[np.ndarray, pd.Series]] = None,
        coefficient_of_variation: Optional[float] = None,
    ) -> float:
        """
        Compute full credibility standard n*.
        
        If claim_amounts or CV is supplied, adjusts for severity variance:
        n* = n_0 * (1 + CV^2)
        """
        if coefficient_of_variation is not None:
            cv = coefficient_of_variation
        elif claim_amounts is not None and len(claim_amounts) > 1:
            arr = np.asarray(claim_amounts, dtype=float)
            mean_val = np.mean(arr)
            std_val = np.std(arr, ddof=1)
            cv = float(std_val / mean_val) if mean_val > 0 else 0.0
        else:
            cv = 0.0

        n_star = self.base_full_cred_count * (1.0 + (cv ** 2))
        return float(n_star)

    def evaluate(
        self,
        observed_value: float,
        prior_mean: float,
        observed_count: float,
        claim_amounts: Optional[Union[np.ndarray, pd.Series]] = None,
        cv: Optional[float] = None,
    ) -> CredibilityResult:
        """
        Evaluate limited fluctuation credibility and blend observed with prior mean.
        """
        n_star = self.calculate_full_credibility_standard(claim_amounts=claim_amounts, coefficient_of_variation=cv)
        
        if observed_count <= 0:
            z = 0.0
        else:
            z = min(1.0, np.sqrt(observed_count / n_star))

        cred_est = z * observed_value + (1.0 - z) * prior_mean

        return CredibilityResult(
            credibility_factor=float(z),
            observed_statistic=float(observed_value),
            prior_mean=float(prior_mean),
            credibility_weighted_estimate=float(cred_est),
            full_credibility_standard=float(n_star),
            sample_size=float(observed_count),
            is_fully_credible=bool(z >= 1.0),
            variance_components={"z_critical": self.z_crit, "cv": cv if cv is not None else 0.0},
        )


class BuhlmannStraubCredibility:
    """
    Bühlmann-Straub Credibility (Empirical Bayes Nonparametric Model).
    
    Decomposes total variability into:
    - s^2: Expected Value of Process Variance (EPV / within-group risk fluctuation)
    - a: Variance of Hypothetical Means (VHM / between-group structural heterogeneity)
    
    Credibility factor:
        Z_i = P_i / (P_i + s^2 / a) = P_i / (P_i + k*)
    """

    def __init__(self, eps: float = 1e-12):
        self.eps = eps
        self.s2: Optional[float] = None  # EPV
        self.a: Optional[float] = None   # VHM
        self.k_star: Optional[float] = None
        self.mu_bar: Optional[float] = None

    def fit(
        self,
        df: pd.DataFrame,
        group_col: str,
        loss_ratio_col: str,
        exposure_col: str,
    ) -> Dict[str, Any]:
        """
        Fit the Bühlmann-Straub empirical Bayes parameters from panel experience.
        
        Parameters
        ----------
        df : pd.DataFrame
            Longitudinal experience table with groups (cedants/treaties),
            loss ratio/rate, and exposure weights.
        """
        data = df[[group_col, loss_ratio_col, exposure_col]].dropna().copy()
        data[exposure_col] = pd.to_numeric(data[exposure_col], errors="coerce")
        data[loss_ratio_col] = pd.to_numeric(data[loss_ratio_col], errors="coerce")
        data = data[data[exposure_col] > 0]

        groups = data.groupby(group_col)
        k = len(groups)
        if k < 2:
            raise ValueError("Bühlmann-Straub requires at least 2 distinct groups.")

        # Group-level totals
        # P_{i.} = sum_t P_{it}
        # X_{i.} = sum_t (P_{it} * X_{it}) / P_{i.}
        group_p = groups[exposure_col].sum()
        group_xp = groups.apply(lambda g: (g[exposure_col] * g[loss_ratio_col]).sum())
        group_x_bar = group_xp / group_p

        p_total = group_p.sum()
        mu_bar = float(group_xp.sum() / p_total)
        self.mu_bar = mu_bar

        # Step 1: Calculate s^2 (Expected Process Variance - EPV)
        # s^2 = 1 / sum(n_i - 1) * sum_i sum_t P_{it} (X_{it} - X_{i.})^2
        numerator_s2 = 0.0
        degrees_of_freedom = 0

        for grp_name, grp_df in groups:
            n_i = len(grp_df)
            if n_i > 1:
                x_bar_i = group_x_bar[grp_name]
                sq_diff = grp_df[exposure_col] * ((grp_df[loss_ratio_col] - x_bar_i) ** 2)
                numerator_s2 += sq_diff.sum()
                degrees_of_freedom += (n_i - 1)

        if degrees_of_freedom > 0:
            s2 = float(numerator_s2 / degrees_of_freedom)
        else:
            # Fallback if only single observations per group
            s2 = float(np.var(data[loss_ratio_col], ddof=1) * np.mean(data[exposure_col]))

        self.s2 = max(s2, self.eps)

        # Step 2: Calculate a (Variance of Hypothetical Means - VHM)
        # a = 1 / P* [ sum_i P_{i.} (X_{i.} - mu_bar)^2 - (k - 1) s^2 ]
        # where P* = P_{..} - sum_i P_{i.}^2 / P_{..}
        p_star = float(p_total - (group_p ** 2).sum() / p_total)
        
        sum_between_variation = float((group_p * ((group_x_bar - mu_bar) ** 2)).sum())
        a_numerator = sum_between_variation - (k - 1) * self.s2

        if p_star > 0:
            a_val = max(0.0, a_numerator / p_star)
        else:
            a_val = 0.0

        self.a = a_val

        # Step 3: Credibility constant k* = s^2 / a
        if self.a > self.eps:
            self.k_star = float(self.s2 / self.a)
        else:
            self.k_star = float("inf")  # Pure prior mean, no credibility to individual group

        return {
            "epv_s2": self.s2,
            "vhm_a": self.a,
            "buhlmann_constant_k": self.k_star,
            "collective_mean_mu": self.mu_bar,
            "group_count": k,
        }

    def predict_group(self, exposure: float, observed_mean: float) -> CredibilityResult:
        """
        Compute credibility for a specific group given exposure and observed mean.
        """
        if self.s2 is None or self.mu_bar is None:
            raise RuntimeError("Model must be fitted via fit() before calling predict_group()")

        if np.isinf(self.k_star) or self.k_star is None:
            z = 0.0
        else:
            z = float(exposure / (exposure + self.k_star))

        cred_est = z * observed_mean + (1.0 - z) * self.mu_bar

        return CredibilityResult(
            credibility_factor=z,
            observed_statistic=observed_mean,
            prior_mean=self.mu_bar,
            credibility_weighted_estimate=cred_est,
            full_credibility_standard=float(self.k_star * 99.0) if self.k_star and not np.isinf(self.k_star) else float("inf"),
            sample_size=exposure,
            variance_components={"epv_s2": self.s2, "vhm_a": self.a, "k_star": self.k_star},
            is_fully_credible=bool(z >= 0.99),
        )
