"""
Actuarial GLM Modeling & Survival Experience Analysis
======================================================

Provides:
1. Poisson & Negative Binomial GLMs with log-exposure offset for mortality & lapse relativities
2. Kaplan-Meier survival curves with Greenwood's variance formula
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


class ActuarialGLMExperience:
    """
    Actuarial Generalized Linear Model (GLM) for experience study relativity pricing.
    
    Fits:
    - Poisson GLM with log(exposure) offset:
      ln(E[Claims]) = ln(Exposure) + beta_0 + sum(beta_i * X_i)
    - Negative Binomial GLM for overdispersed experience
    """

    def __init__(self, family: str = "poisson"):
        self.family_type = family.lower()
        self.model = None
        self.results = None

    def fit(
        self,
        df: pd.DataFrame,
        formula: str,
        exposure_col: str = "exposure_years",
    ) -> Dict[str, Any]:
        """
        Fit the actuarial GLM with log-exposure offset.
        
        Parameters
        ----------
        df : pd.DataFrame
            Actuarial portfolio experience table.
        formula : str
            Statsmodels formula, e.g. "actual_claims ~ C(gender) + C(smoker) + attained_age"
        exposure_col : str
            Column holding exposure in years (must be > 0).
        """
        data = df[df[exposure_col] > 0].copy()
        offset = np.log(data[exposure_col].values.astype(float))

        if self.family_type == "negative_binomial" or self.family_type == "nb":
            fam = sm.families.NegativeBinomial()
        else:
            fam = sm.families.Poisson()

        self.model = smf.glm(formula=formula, data=data, offset=offset, family=fam)
        self.results = self.model.fit()

        # Multiplicative relativities: exp(beta)
        params = self.results.params
        conf_int = self.results.conf_int()
        relativities = pd.DataFrame({
            "Coefficient": params,
            "Std_Error": self.results.bse,
            "z_value": self.results.tvalues,
            "p_value": self.results.pvalues,
            "Relativity_exp_beta": np.exp(params),
            "Relativity_CI_low": np.exp(conf_int[0]),
            "Relativity_CI_high": np.exp(conf_int[1]),
        })

        return {
            "family": self.family_type,
            "aic": self.results.aic,
            "bic": self.results.bic_llf,
            "deviance": self.results.deviance,
            "df_resid": self.results.df_resid,
            "relativities": relativities,
            "summary_text": str(self.results.summary()),
        }


class SurvivalExperienceAnalyzer:
    """
    Nonparametric Survival Analysis for Reinsurance Portfolios.
    
    Implements Kaplan-Meier Product-Limit Estimator with Greenwood's formula
    for variance and 95% confidence bands.
    """

    @staticmethod
    def kaplan_meier(
        durations: np.ndarray | pd.Series,
        events: np.ndarray | pd.Series,
    ) -> pd.DataFrame:
        """
        Calculate Kaplan-Meier survival curve S(t) and standard error.
        
        Parameters
        ----------
        durations : array-like
            Observed follow-up time (e.g. policy years or months).
        events : array-like
            1 if event occurred (death or lapse), 0 if censored.
        """
        t = np.asarray(durations, dtype=float)
        d = np.asarray(events, dtype=int)

        df_surv = pd.DataFrame({"time": t, "event": d})
        # Sort by time
        df_surv = df_surv.sort_values(by="time")

        # Aggregate at each unique event time
        unique_times = np.sort(df_surv["time"].unique())
        n_total = len(df_surv)

        records = []
        s_prev = 1.0
        greenwood_sum = 0.0

        for ut in unique_times:
            # Number at risk right before ut
            n_at_risk = (df_surv["time"] >= ut).sum()
            # Events at ut
            d_events = ((df_surv["time"] == ut) & (df_surv["event"] == 1)).sum()
            c_censored = ((df_surv["time"] == ut) & (df_surv["event"] == 0)).sum()

            if n_at_risk <= 0:
                continue

            hazard = d_events / n_at_risk
            s_t = s_prev * (1.0 - hazard)

            if n_at_risk > d_events and d_events > 0:
                greenwood_sum += d_events / (n_at_risk * (n_at_risk - d_events))

            se_st = s_t * np.sqrt(greenwood_sum)
            ci_low = max(0.0, s_t - 1.96 * se_st)
            ci_high = min(1.0, s_t + 1.96 * se_st)

            records.append({
                "time": ut,
                "n_at_risk": n_at_risk,
                "events": d_events,
                "censored": c_censored,
                "survival_prob": s_t,
                "std_err": se_st,
                "ci_lower": ci_low,
                "ci_upper": ci_high,
            })
            s_prev = s_t

        return pd.DataFrame(records)
