"""
Reinsurance Treaty Structures
=============================

Mathematical implementation of standard reinsurance treaty types:
- Quota Share (Proportional)
- Surplus (Proportional)
- Excess of Loss (Non-Proportional / Per-Risk and Per-Occurrence)
- Aggregate Stop Loss
- Reinsurance Program composition
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from reinsurance_analytics.treaty.reinstatements import ReinstatementClause


@dataclass
class TreatyRecoveryResult:
    """Breakdown of loss recovery through treaty layer."""
    gross_loss: float
    ceded_loss: float
    retained_loss: float
    reinstatement_premium_paid: float = 0.0


class ReinsuranceTreaty(ABC):
    """Abstract Base Class for reinsurance contracts."""

    @abstractmethod
    def evaluate_loss(self, gross_loss: float | np.ndarray) -> np.ndarray:
        """Calculate ceded recoveries for given gross loss amounts."""
        pass


class QuotaShareTreaty(ReinsuranceTreaty):
    """
    Quota Share (Proportional) Reinsurance Treaty.
    
    Parameters
    ----------
    cession_rate : float
        Percentage of risk ceded to reinsurer (0.0 to 1.0).
    ceding_commission : float
        Commission paid by reinsurer to cedant (e.g. 0.25 = 25%).
    profit_commission : float
        Profit commission percentage on positive underwriting margin.
    """

    def __init__(
        self,
        cession_rate: float,
        ceding_commission: float = 0.25,
        profit_commission: float = 0.0,
        name: str = "Quota Share Treaty",
    ):
        if not (0.0 <= cession_rate <= 1.0):
            raise ValueError("cession_rate must be between 0.0 and 1.0")
        self.cession_rate = float(cession_rate)
        self.retention_rate = 1.0 - self.cession_rate
        self.ceding_commission = float(ceding_commission)
        self.profit_commission = float(profit_commission)
        self.name = name

    def evaluate_loss(self, gross_loss: float | np.ndarray) -> np.ndarray:
        gross = np.asarray(gross_loss, dtype=float)
        return self.cession_rate * gross

    def evaluate_retained_loss(self, gross_loss: float | np.ndarray) -> np.ndarray:
        gross = np.asarray(gross_loss, dtype=float)
        return self.retention_rate * gross

    def evaluate_treaty_cashflow(self, gross_premium: float, gross_losses: float) -> Dict[str, float]:
        ceded_prem = self.cession_rate * gross_premium
        ced_comm = ceded_prem * self.ceding_commission
        ceded_loss = self.cession_rate * gross_losses
        net_reinsurance_margin = ceded_prem - ced_comm - ceded_loss
        
        profit_comm = max(0.0, net_reinsurance_margin * self.profit_commission)
        reinsurer_profit = net_reinsurance_margin - profit_comm

        return {
            "ceded_premium": ceded_prem,
            "ceding_commission": ced_comm,
            "ceded_losses": ceded_loss,
            "profit_commission": profit_comm,
            "reinsurer_underwriting_profit": reinsurer_profit,
            "cedant_net_losses": self.retention_rate * gross_losses,
        }


class SurplusTreaty(ReinsuranceTreaty):
    """
    Surplus (Proportional) Reinsurance Treaty.
    
    Cedant retains up to line retention R.
    Surplus lines (up to n lines) are ceded to the reinsurer.
    """

    def __init__(self, line_retention: float, num_lines: int = 4, name: str = "Surplus Treaty"):
        if line_retention <= 0 or num_lines <= 0:
            raise ValueError("line_retention and num_lines must be positive")
        self.line_retention = float(line_retention)
        self.num_lines = int(num_lines)
        self.max_capacity = self.line_retention * (self.num_lines + 1)
        self.name = name

    def get_cession_fraction(self, sum_insured: float | np.ndarray) -> np.ndarray:
        si = np.asarray(sum_insured, dtype=float)
        surplus = np.maximum(0.0, si - self.line_retention)
        max_surplus = self.line_retention * self.num_lines
        ceded_amount = np.minimum(surplus, max_surplus)
        return np.where(si > 0, ceded_amount / si, 0.0)

    def evaluate_loss(self, gross_loss: float | np.ndarray, sum_insured: Optional[float | np.ndarray] = None) -> np.ndarray:
        loss = np.asarray(gross_loss, dtype=float)
        if sum_insured is None:
            # Assume loss itself is the risk unit sum insured
            frac = self.get_cession_fraction(loss)
        else:
            frac = self.get_cession_fraction(sum_insured)
        return frac * loss


class ExcessOfLossTreaty(ReinsuranceTreaty):
    """
    Excess of Loss (Non-Proportional) Treaty (Per Risk or Per Occurrence).
    
    Structure: Limit xs Attachment ($L xs $A).
    Layer Recovery per loss = min(max(0, Loss - Attachment), Limit)
    """

    def __init__(
        self,
        attachment: float,
        limit: float,
        rate_on_line: float = 0.08,
        reinstatement_clause: Optional[ReinstatementClause] = None,
        name: str = "Excess of Loss Layer",
    ):
        if attachment < 0 or limit <= 0:
            raise ValueError("attachment must be >= 0 and limit must be > 0")
        self.attachment = float(attachment)
        self.limit = float(limit)
        self.rate_on_line = float(rate_on_line)
        self.reinstatement_clause = reinstatement_clause or ReinstatementClause(count=1, rate=1.0)
        self.name = name
        self.initial_premium = self.limit * self.rate_on_line

    def evaluate_loss(self, gross_loss: float | np.ndarray) -> np.ndarray:
        gross = np.asarray(gross_loss, dtype=float)
        excess = np.maximum(0.0, gross - self.attachment)
        return np.minimum(excess, self.limit)

    def evaluate_claim_stream(self, claim_stream: List[float] | np.ndarray) -> Dict[str, Any]:
        """
        Process a chronological stream of claims, taking into account limit erosion
        and reinstatement premiums.
        """
        claims = np.asarray(claim_stream, dtype=float)
        total_ceded = 0.0
        reinstatement_premiums = 0.0
        remaining_reinstatements = self.reinstatement_clause.count
        available_limit = self.limit

        for loss in claims:
            if loss <= self.attachment or available_limit <= 0:
                continue

            raw_recovery = min(max(0.0, loss - self.attachment), self.limit)
            recovery = min(raw_recovery, available_limit)
            total_ceded += recovery
            available_limit -= recovery

            # Reinstatement
            if remaining_reinstatements > 0 and recovery > 0:
                reinst_prem = self.reinstatement_clause.calculate_reinstatement_premium(
                    claim_ceded=recovery,
                    layer_limit=self.limit,
                    initial_premium=self.initial_premium,
                )
                reinstatement_premiums += reinst_prem
                remaining_reinstatements -= 1
                available_limit += recovery  # Limit is reinstated

        return {
            "initial_premium": self.initial_premium,
            "reinstatement_premiums": reinstatement_premiums,
            "total_ceded_recoveries": total_ceded,
            "net_reinsurer_margin": (self.initial_premium + reinstatement_premiums) - total_ceded,
        }


class StopLossTreaty(ReinsuranceTreaty):
    """
    Aggregate Stop Loss Treaty.
    
    Attaches when aggregate portfolio loss exceeds aggregate attachment.
    """

    def __init__(self, aggregate_attachment: float, aggregate_limit: float, name: str = "Stop Loss"):
        self.attachment = float(aggregate_attachment)
        self.limit = float(aggregate_limit)
        self.name = name

    def evaluate_loss(self, aggregate_gross_loss: float | np.ndarray) -> np.ndarray:
        agg = np.asarray(aggregate_gross_loss, dtype=float)
        return np.minimum(np.maximum(0.0, agg - self.attachment), self.limit)


class ReinsuranceProgram:
    """
    Composes multiple layers into a complete reinsurance treaty structure:
    e.g., Quota share cession -> Working Layer XL -> Mezzanine XL -> Cat XL -> Cedant Retained Net.
    """

    def __init__(self, layers: Optional[List[ReinsuranceTreaty]] = None):
        self.layers: List[ReinsuranceTreaty] = layers or []

    def add_layer(self, layer: ReinsuranceTreaty) -> None:
        self.layers.append(layer)

    def evaluate(self, gross_losses: np.ndarray) -> pd.DataFrame:
        """
        Evaluate full cascade of reinsurance recoveries and cedant retention.
        """
        gross = np.asarray(gross_losses, dtype=float)
        df_res = pd.DataFrame({"Gross_Loss": gross})

        total_ceded = np.zeros_like(gross)
        for i, lyr in enumerate(self.layers):
            layer_name = getattr(lyr, "name", f"Layer_{i+1}")
            c_loss = lyr.evaluate_loss(gross)
            df_res[f"Ceded_{layer_name}"] = c_loss
            total_ceded += c_loss

        df_res["Total_Ceded"] = total_ceded
        df_res["Net_Retained"] = gross - total_ceded
        return df_res
