"""
Parametric and Benchmark Actuarial Mortality Tables
===================================================

Provides mortality rate lookups and parametric formulations:
- Gompertz-Makeham analytical mortality model
- SOA 2015 VBT (Valuation Basic Table) style select and ultimate benchmark
- Smoker, gender, and underwriting class adjustments
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


class GompertzMakehamTable:
    """
    Gompertz-Makeham Mortality Law:
    Force of mortality: mu_x = A + B * c^x
    
    Exact 1-year death probability:
    q_x = 1 - exp(- A - (B * c^x * (c - 1)) / ln(c))
    """

    def __init__(
        self,
        A: float = 0.0003,      # Extrinsic baseline accident/illness hazard
        B: float = 0.000035,    # Aging multiplier
        c: float = 1.095,       # Rate of senescent deterioration
        name: str = "Standard Gompertz-Makeham",
    ):
        self.A = A
        self.B = B
        self.c = c
        self.name = name

    def force_of_mortality(self, age: float | np.ndarray) -> np.ndarray:
        """Calculate continuous hazard rate mu_x."""
        age_arr = np.asarray(age, dtype=float)
        return self.A + self.B * (self.c ** age_arr)

    def q_x(self, age: float | np.ndarray) -> np.ndarray:
        """
        Calculate exact 1-year mortality probability q_x.
        """
        age_arr = np.asarray(age, dtype=float)
        ln_c = np.log(self.c)
        integral = self.A + (self.B * (self.c ** age_arr) * (self.c - 1.0)) / ln_c
        qx = 1.0 - np.exp(-integral)
        return np.clip(qx, 0.0, 1.0)


class SOAVBTBenchmark:
    """
    Actuarial benchmark table modeled after the Society of Actuaries (SOA)
    2015 Valuation Basic Table (VBT).
    
    Supports:
    - Age range 18 to 95
    - Gender: Male / Female
    - Smoking Status: Non-Smoker / Smoker
    - Underwriting Class: Preferred Plus, Preferred, Standard, Substandard
    - Select Period duration adjustment (Underwriting effect)
    """

    # Typical duration selection factors for individual life reinsurance
    SELECT_FACTORS: Dict[int, float] = {
        1: 0.60,
        2: 0.70,
        3: 0.80,
        4: 0.90,
        5: 1.00,
    }

    # Underwriting rating multipliers
    UW_CLASS_MULTIPLIERS: Dict[str, float] = {
        "PREFERRED_PLUS": 0.70,
        "PREFERRED": 0.85,
        "STANDARD": 1.00,
        "SUBSTANDARD": 1.75,
    }

    def __init__(self):
        # Parametric base curves calibrated to standard SOA population benchmarks
        # Male Non-Smoker
        self.base_male_ns = GompertzMakehamTable(A=0.00025, B=0.000030, c=1.092, name="Male Non-Smoker Base")
        # Female Non-Smoker (~30-40% lower mortality at younger/middle ages)
        self.base_female_ns = GompertzMakehamTable(A=0.00018, B=0.000022, c=1.093, name="Female Non-Smoker Base")
        # Smoker multiplier baseline: ~1.85x - 2.2x
        self.smoker_multiplier = 2.05

    def get_qx(
        self,
        age: int | float | np.ndarray,
        gender: str = "M",
        smoker: str = "NS",
        uw_class: str = "STANDARD",
        duration: Optional[int] = None,
    ) -> np.ndarray:
        """
        Calculate expected annual mortality rate q_x for specified cohort.
        
        Parameters
        ----------
        age : int | float | np.ndarray
            Attained age.
        gender : str
            'M' for Male, 'F' for Female.
        smoker : str
            'NS' for Non-Smoker, 'SM' for Smoker.
        uw_class : str
            'PREFERRED_PLUS', 'PREFERRED', 'STANDARD', 'SUBSTANDARD'
        duration : Optional[int]
            Policy duration (policy year) for select period discounting.
        """
        age_arr = np.asarray(age, dtype=float)
        gender_up = str(gender).upper()
        smoker_up = str(smoker).upper()
        uw_up = str(uw_class).upper()

        if "F" in gender_up:
            base_table = self.base_female_ns
        else:
            base_table = self.base_male_ns

        base_qx = base_table.q_x(age_arr)

        # Smoker adjustment
        if smoker_up in ("SM", "S", "SMOKER", "YES", "TRUE", "1"):
            base_qx = base_qx * self.smoker_multiplier

        # Underwriting class adjustment
        uw_factor = self.UW_CLASS_MULTIPLIERS.get(uw_up, 1.00)
        adjusted_qx = base_qx * uw_factor

        # Select period duration adjustment
        if duration is not None and duration > 0:
            dur_key = min(duration, 5)
            sel_factor = self.SELECT_FACTORS.get(dur_key, 1.00)
            adjusted_qx = adjusted_qx * sel_factor

        return np.clip(adjusted_qx, 0.0, 1.0)

    def attach_expected_rates(
        self,
        df: pd.DataFrame,
        age_col: str = "attained_age",
        gender_col: str = "gender",
        smoker_col: str = "smoker",
        uw_col: str = "underwriting_class",
        duration_col: Optional[str] = "policy_year",
        exposure_col: str = "exposure_years",
        face_amount_col: Optional[str] = "face_amount",
    ) -> pd.DataFrame:
        """
        Vectorized attachment of expected mortality rates and expected claims.
        """
        df_out = df.copy()

        q_expected = []
        for _, row in df_out.iterrows():
            age = row[age_col]
            gender = row.get(gender_col, "M")
            smoker = row.get(smoker_col, "NS")
            uw = row.get(uw_col, "STANDARD")
            dur = row.get(duration_col, None) if duration_col in df_out.columns else None

            qx = float(self.get_qx(age=age, gender=gender, smoker=smoker, uw_class=uw, duration=dur))
            q_expected.append(qx)

        df_out["expected_qx"] = np.array(q_expected)
        df_out["expected_claims_count"] = df_out[exposure_col] * df_out["expected_qx"]

        if face_amount_col and face_amount_col in df_out.columns:
            if "ceded_amount" in df_out.columns:
                df_out["expected_claims_ceded"] = df_out["ceded_exposure"] * df_out["expected_qx"]
            df_out["expected_claims_amount"] = df_out["amount_exposure"] * df_out["expected_qx"]

        return df_out
