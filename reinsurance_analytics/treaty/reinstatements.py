"""
Reinsurance Treaty Reinstatement Provisions
===========================================

Calculates reinstatement premiums and layer erosion:
- Pro-rata as to amount
- Pro-rata as to time and amount
- Free reinstatements (0%)
- Reinstatement count exhaustion tracking
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ReinstatementType(str, Enum):
    PRO_RATA_AMOUNT = "pro_rata_amount"
    PRO_RATA_TIME_AMOUNT = "pro_rata_time_amount"
    FREE = "free"


@dataclass
class ReinstatementClause:
    """
    Defines reinstatement conditions for an Excess of Loss treaty.
    
    Parameters
    ----------
    count : int
        Number of reinstatements permitted (e.g. 1, 2, or unlimited).
    rate : float
        Reinstatement rate percentage of original premium (e.g. 1.0 for 100%, 0.5 for 50%, 0.0 for free).
    reinstatement_type : ReinstatementType
        Type of proration.
    """
    count: int = 1
    rate: float = 1.0
    reinstatement_type: ReinstatementType = ReinstatementType.PRO_RATA_AMOUNT

    def calculate_reinstatement_premium(
        self,
        claim_ceded: float,
        layer_limit: float,
        initial_premium: float,
        fraction_of_year_remaining: float = 1.0,
    ) -> float:
        """
        Compute reinstatement premium payable upon a ceded claim.
        """
        if self.count <= 0 or self.rate <= 0 or layer_limit <= 0:
            return 0.0

        fraction_consumed = min(1.0, claim_ceded / layer_limit)

        if self.reinstatement_type == ReinstatementType.PRO_RATA_AMOUNT:
            return fraction_consumed * self.rate * initial_premium

        elif self.reinstatement_type == ReinstatementType.PRO_RATA_TIME_AMOUNT:
            return fraction_consumed * fraction_of_year_remaining * self.rate * initial_premium

        elif self.reinstatement_type == ReinstatementType.FREE:
            return 0.0

        return 0.0
