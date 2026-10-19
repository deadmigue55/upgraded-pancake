"""
Treaty Loss Experience Analysis & Burning Cost Rating
======================================================

Analyzes historical loss experience for reinsurance treaties:
- Historical loss indexing / trend adjustment
- Burning cost calculation across treaty excess-of-loss layers
- Attritional vs large loss decomposition
- Experience loss ratio and technical rate indication
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


@dataclass
class BurningCostResult:
    """Treaty burning cost experience output."""
    layer_attachment: float
    layer_limit: float
    annual_experience: pd.DataFrame
    average_burning_cost_rate: float
    volatility_coefficient: float
    loaded_technical_rate: float
    total_ceded_losses: float
    total_subject_premium: float


class TreatyLossExperienceStudy:
    """
    Experience Analysis engine for Non-Life / Treaty Reinsurance.
    """

    def __init__(self, inflation_rate: float = 0.03, expense_loading: float = 0.15, profit_margin: float = 0.10):
        self.inflation_rate = inflation_rate
        self.expense_loading = expense_loading
        self.profit_margin = profit_margin

    def trend_losses(
        self,
        claims_df: pd.DataFrame,
        loss_date_col: str,
        loss_amount_col: str,
        target_year: int,
    ) -> pd.DataFrame:
        """
        Trend historical losses to prospective pricing year using compound inflation.
        """
        df = claims_df.copy()
        df["claim_year"] = pd.to_datetime(df[loss_date_col]).dt.year
        df["years_to_target"] = target_year - df["claim_year"]
        df["trend_factor"] = (1.0 + self.inflation_rate) ** np.maximum(0, df["years_to_target"])
        df["trended_loss"] = df[loss_amount_col] * df["trend_factor"]
        return df

    def evaluate_excess_layer_burning_cost(
        self,
        claims_df: pd.DataFrame,
        premiums_df: pd.DataFrame,
        attachment: float,
        limit: float,
        year_col: str = "year",
        trended_loss_col: str = "trended_loss",
        subject_premium_col: str = "subject_premium",
    ) -> BurningCostResult:
        """
        Calculate historical burning cost for an Excess of Loss layer (Limit xs Attachment).
        
        Layer recovery per claim:
            Recovery = min(max(0, Loss - Attachment), Limit)
        """
        df_claims = claims_df.copy()
        df_prem = premiums_df.copy()

        # Compute layer recovery per claim
        losses = df_claims[trended_loss_col].values
        recoveries = np.minimum(np.maximum(0.0, losses - attachment), limit)
        df_claims["layer_recovery"] = recoveries

        # Aggregate recoveries by accident year
        claims_by_year = df_claims.groupby(year_col)["layer_recovery"].agg(["sum", "count"]).reset_index()
        claims_by_year.rename(columns={"sum": "ceded_recovery", "count": "claim_count"}, inplace=True)

        # Merge with subject premium
        merged = pd.merge(df_prem[[year_col, subject_premium_col]], claims_by_year, on=year_col, how="left")
        merged["ceded_recovery"] = merged["ceded_recovery"].fillna(0.0)
        merged["claim_count"] = merged["claim_count"].fillna(0)

        # Annual burning cost rate
        merged["burning_cost_rate"] = merged["ceded_recovery"] / merged[subject_premium_col]

        tot_recovery = float(merged["ceded_recovery"].sum())
        tot_prem = float(merged[subject_premium_col].sum())
        avg_bc_rate = tot_recovery / tot_prem if tot_prem > 0 else 0.0

        # Burning cost volatility
        bc_rates = merged["burning_cost_rate"].values
        cv = float(np.std(bc_rates, ddof=1) / avg_bc_rate) if avg_bc_rate > 0 and len(bc_rates) > 1 else 0.0

        # Loaded technical rate: (Burning Cost * (1 + Risk Load)) / (1 - Expense Load)
        risk_load = 0.5 * cv * avg_bc_rate
        loaded_rate = (avg_bc_rate + risk_load) / (1.0 - self.expense_loading - self.profit_margin)

        return BurningCostResult(
            layer_attachment=attachment,
            layer_limit=limit,
            annual_experience=merged,
            average_burning_cost_rate=avg_bc_rate,
            volatility_coefficient=cv,
            loaded_technical_rate=loaded_rate,
            total_ceded_losses=tot_recovery,
            total_subject_premium=tot_prem,
        )
