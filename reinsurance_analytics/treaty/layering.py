"""
Reinsurance Layer Stack
=======================

Manages multi-tier non-proportional Excess of Loss programs.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from reinsurance_analytics.treaty.structures import ExcessOfLossTreaty


class ReinsuranceLayerStack:
    """
    Manages ordered Excess of Loss towers / treaty programs.
    """

    def __init__(self, layers: Optional[List[ExcessOfLossTreaty]] = None):
        self.layers: List[ExcessOfLossTreaty] = sorted(layers or [], key=lambda l: l.attachment)

    def add_layer(self, layer: ExcessOfLossTreaty) -> None:
        self.layers.append(layer)
        self.layers.sort(key=lambda l: l.attachment)

    def evaluate_losses(self, gross_claims: np.ndarray) -> pd.DataFrame:
        claims = np.asarray(gross_claims, dtype=float)
        results = {"Gross_Loss": claims}
        total_ceded = np.zeros_like(claims)

        for lyr in self.layers:
            ceded = lyr.evaluate_loss(claims)
            results[lyr.name] = ceded
            total_ceded += ceded

        results["Total_Ceded"] = total_ceded
        results["Cedant_Net_Loss"] = claims - total_ceded
        return pd.DataFrame(results)

    def summary(self) -> pd.DataFrame:
        """Tabular summary of treaty tower."""
        records = []
        for lyr in self.layers:
            records.append({
                "Layer_Name": lyr.name,
                "Attachment": lyr.attachment,
                "Limit": lyr.limit,
                "Top_of_Layer": lyr.attachment + lyr.limit,
                "Rate_on_Line": lyr.rate_on_line,
                "Initial_Premium": lyr.initial_premium,
                "Reinstatements": lyr.reinstatement_clause.count,
                "Reinstatement_Rate": lyr.reinstatement_clause.rate,
            })
        return pd.DataFrame(records)
