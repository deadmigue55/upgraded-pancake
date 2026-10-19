"""
Actuarial Life & Health Reinsurance Experience Study
====================================================

Calculates:
- Actual-to-Expected (A/E) ratios by count and by amount (Gross, Retained, Ceded)
- Garwood exact Poisson confidence intervals (SOA standard)
- Limited Fluctuation credibility-adjusted expected basis
- Multi-dimensional slicing (Attained Age, Duration, Smoker, Gender, Rating Class)
- Goodness-of-fit statistical hypothesis testing (Pearson Chi-Square test)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from scipy import stats

from reinsurance_analytics.core.credibility import LimitedFluctuationCredibility


@dataclass
class ExperienceStudyResult:
    """Detailed summary container for experience study results."""
    summary_table: pd.DataFrame
    total_exposure_years: float
    actual_claims_count: int
    expected_claims_count: float
    ae_ratio_count: float
    ae_count_ci_lower: float
    ae_count_ci_upper: float
    actual_claims_amount: float
    expected_claims_amount: float
    ae_ratio_amount: float
    overall_credibility_z: float
    credibility_adjusted_ae: float
    chi_square_statistic: float
    chi_square_p_value: float
    group_dimensions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_exposure_years": round(self.total_exposure_years, 2),
            "actual_claims_count": int(self.actual_claims_count),
            "expected_claims_count": round(self.expected_claims_count, 2),
            "ae_ratio_count": round(self.ae_ratio_count, 4),
            "ae_count_95ci": [round(self.ae_count_ci_lower, 4), round(self.ae_count_ci_upper, 4)],
            "actual_claims_amount": round(self.actual_claims_amount, 2),
            "expected_claims_amount": round(self.expected_claims_amount, 2),
            "ae_ratio_amount": round(self.ae_ratio_amount, 4),
            "overall_credibility_z": round(self.overall_credibility_z, 4),
            "credibility_adjusted_ae": round(self.credibility_adjusted_ae, 4),
            "chi_square_stat": round(self.chi_square_statistic, 4),
            "chi_square_p_value": round(self.chi_square_p_value, 6),
            "group_dimensions": self.group_dimensions,
        }


class LifeExperienceStudy:
    """
    Experience Study Engine for Life and Health Reinsurance Treaties.
    """

    def __init__(
        self,
        confidence_level: float = 0.95,
        credibility_evaluator: Optional[LimitedFluctuationCredibility] = None,
    ):
        self.confidence_level = confidence_level
        self.credibility_engine = credibility_evaluator or LimitedFluctuationCredibility(
            confidence_level=0.90, error_margin=0.05
        )

    def calculate_poisson_ci(self, actual: float, expected: float) -> tuple[float, float]:
        """
        Garwood exact Poisson confidence interval for Actual-to-Expected ratio.
        
        Uses Chi-Square distribution:
        Lower: 0.5 * chi2.ppf(alpha/2, 2 * A) / E
        Upper: 0.5 * chi2.ppf(1 - alpha/2, 2 * (A + 1)) / E
        """
        if expected <= 0:
            return (0.0, 0.0)

        alpha = 1.0 - self.confidence_level

        if actual == 0:
            lower = 0.0
            upper = 0.5 * stats.chi2.ppf(1.0 - alpha, 2) / expected
        else:
            lower = 0.5 * stats.chi2.ppf(alpha / 2.0, 2 * actual) / expected
            upper = 0.5 * stats.chi2.ppf(1.0 - alpha / 2.0, 2 * (actual + 1)) / expected

        return float(lower), float(upper)

    def analyze(
        self,
        df: pd.DataFrame,
        group_cols: Optional[List[str]] = None,
        actual_count_col: str = "is_death",
        expected_count_col: str = "expected_claims_count",
        exposure_col: str = "exposure_years",
        actual_amount_col: Optional[str] = "claim_amount_gross",
        expected_amount_col: Optional[str] = "expected_claims_amount",
    ) -> ExperienceStudyResult:
        """
        Conduct complete actuarial experience study across specified segments.
        """
        cols = list(group_cols) if group_cols else []
        
        # Portfolio aggregate totals
        total_exp = float(df[exposure_col].sum())
        total_act_cnt = float(df[actual_count_col].sum())
        total_exp_cnt = float(df[expected_count_col].sum())

        ae_cnt = (total_act_cnt / total_exp_cnt) if total_exp_cnt > 0 else 0.0
        ci_lower, ci_upper = self.calculate_poisson_ci(total_act_cnt, total_exp_cnt)

        # Amounts
        if actual_amount_col and actual_amount_col in df.columns:
            total_act_amt = float(df[actual_amount_col].sum())
        else:
            total_act_amt = 0.0

        if expected_amount_col and expected_amount_col in df.columns:
            total_exp_amt = float(df[expected_amount_col].sum())
        else:
            total_exp_amt = 0.0

        ae_amt = (total_act_amt / total_exp_amt) if total_exp_amt > 0 else 0.0

        # Credibility evaluation
        claim_amounts = df[df[actual_count_col] == 1][actual_amount_col] if actual_amount_col in df.columns else None
        cred_res = self.credibility_engine.evaluate(
            observed_value=ae_cnt,
            prior_mean=1.00,  # Expected basis = 100%
            observed_count=total_act_cnt,
            claim_amounts=claim_amounts,
        )

        # Segmented analysis table
        if cols:
            grouped = df.groupby(cols, observed=False)
            records = []

            for name, grp in grouped:
                grp_name = name if isinstance(name, tuple) else (name,)
                g_exp = float(grp[exposure_col].sum())
                g_act_cnt = float(grp[actual_count_col].sum())
                g_exp_cnt = float(grp[expected_count_col].sum())

                g_ae_cnt = (g_act_cnt / g_exp_cnt) if g_exp_cnt > 0 else 0.0
                g_ci_low, g_ci_high = self.calculate_poisson_ci(g_act_cnt, g_exp_cnt)

                g_act_amt = float(grp[actual_amount_col].sum()) if actual_amount_col in grp.columns else 0.0
                g_exp_amt = float(grp[expected_amount_col].sum()) if expected_amount_col in grp.columns else 0.0
                g_ae_amt = (g_act_amt / g_exp_amt) if g_exp_amt > 0 else 0.0

                # Group credibility
                g_claims = grp[grp[actual_count_col] == 1][actual_amount_col] if actual_amount_col in grp.columns else None
                g_cred = self.credibility_engine.evaluate(
                    observed_value=g_ae_cnt,
                    prior_mean=1.00,
                    observed_count=g_act_cnt,
                    claim_amounts=g_claims,
                )

                row_dict = dict(zip(cols, grp_name))
                row_dict.update({
                    "exposure_years": g_exp,
                    "actual_claims": g_act_cnt,
                    "expected_claims": g_exp_cnt,
                    "ae_ratio_count": g_ae_cnt,
                    "ae_ci_lower": g_ci_low,
                    "ae_ci_upper": g_ci_high,
                    "actual_claim_amount": g_act_amt,
                    "expected_claim_amount": g_exp_amt,
                    "ae_ratio_amount": g_ae_amt,
                    "credibility_Z": g_cred.credibility_factor,
                    "credibility_adjusted_ae": g_cred.credibility_weighted_estimate,
                })
                records.append(row_dict)

            summary_df = pd.DataFrame(records)

            # Chi-square goodness-of-fit test across cells: sum((A - E)^2 / E)
            valid_cells = summary_df[summary_df["expected_claims"] > 0]
            if len(valid_cells) > 1:
                chi2_stat = float(((valid_cells["actual_claims"] - valid_cells["expected_claims"]) ** 2 / valid_cells["expected_claims"]).sum())
                df_chi2 = len(valid_cells) - 1
                p_val = float(1.0 - stats.chi2.cdf(chi2_stat, df_chi2))
            else:
                chi2_stat = 0.0
                p_val = 1.0
        else:
            summary_df = pd.DataFrame([{
                "exposure_years": total_exp,
                "actual_claims": total_act_cnt,
                "expected_claims": total_exp_cnt,
                "ae_ratio_count": ae_cnt,
                "ae_ci_lower": ci_lower,
                "ae_ci_upper": ci_upper,
                "actual_claim_amount": total_act_amt,
                "expected_claim_amount": total_exp_amt,
                "ae_ratio_amount": ae_amt,
                "credibility_Z": cred_res.credibility_factor,
                "credibility_adjusted_ae": cred_res.credibility_weighted_estimate,
            }])
            chi2_stat = float(((total_act_cnt - total_exp_cnt) ** 2 / total_exp_cnt)) if total_exp_cnt > 0 else 0.0
            p_val = float(1.0 - stats.chi2.cdf(chi2_stat, 1))

        return ExperienceStudyResult(
            summary_table=summary_df,
            total_exposure_years=total_exp,
            actual_claims_count=int(total_act_cnt),
            expected_claims_count=total_exp_cnt,
            ae_ratio_count=ae_cnt,
            ae_count_ci_lower=ci_lower,
            ae_count_ci_upper=ci_upper,
            actual_claims_amount=total_act_amt,
            expected_claims_amount=total_exp_amt,
            ae_ratio_amount=ae_amt,
            overall_credibility_z=cred_res.credibility_factor,
            credibility_adjusted_ae=cred_res.credibility_weighted_estimate,
            chi_square_statistic=chi2_stat,
            chi_square_p_value=p_val,
            group_dimensions=cols,
        )
