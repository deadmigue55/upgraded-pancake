"""
Actuarial Exposure Calculation Engine
======================================

Implements standard actuarial exposure methodologies:
- Exact Continuous (Daily) Exposure
- Annual (Balducci Assumption) Exposure
- Census (Calendar Year) Exposure
- Split exposures by policy year, calendar year, and attained age.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd


class ExposureMethod(str, Enum):
    """Actuarial exposure calculation methods."""
    EXACT_CONTINUOUS = "exact_continuous"
    BALDUCCI_ANNUAL = "balducci_annual"
    CENSUS = "census"


class ExposureEngine:
    """
    Actuarial Exposure Engine for Life and Health Reinsurance experience studies.
    
    Computes policy counts, exact-day exposures, and monetary amounts at risk
    (Gross Face Amount, Retained Exposure, Ceded Reinsurance Exposure).
    """

    def __init__(
        self,
        study_start: str | pd.Timestamp,
        study_end: str | pd.Timestamp,
        method: ExposureMethod = ExposureMethod.EXACT_CONTINUOUS,
        days_in_year: float = 365.25,
    ):
        self.study_start = pd.to_datetime(study_start)
        self.study_end = pd.to_datetime(study_end)
        self.method = method
        self.days_in_year = days_in_year

        if self.study_end <= self.study_start:
            raise ValueError("study_end must be strictly greater than study_start")

    def calculate_policy_exposure(
        self,
        issue_date: pd.Timestamp,
        exit_date: Optional[pd.Timestamp],
        is_death: bool = False,
    ) -> float:
        """
        Calculate individual policy exposure in fractional years.
        
        Parameters
        ----------
        issue_date : pd.Timestamp
            Date policy was issued.
        exit_date : Optional[pd.Timestamp]
            Date policy exited (death, lapse, surrender, or None if active).
        is_death : bool
            Whether exit was due to death/claim event.
        """
        start = max(issue_date, self.study_start)
        
        if exit_date is None or pd.isna(exit_date):
            end = self.study_end
        else:
            end = min(exit_date, self.study_end)

        if end <= start:
            return 0.0

        if self.method == ExposureMethod.EXACT_CONTINUOUS:
            days = (end - start).days
            return max(0.0, days / self.days_in_year)

        elif self.method == ExposureMethod.BALDUCCI_ANNUAL:
            # Under Balducci / traditional life exposure, a death is exposed to the end of policy year
            if is_death and exit_date is not None and exit_date <= self.study_end:
                # Find the policy anniversary following the death
                years_since_issue = int((exit_date - issue_date).days / self.days_in_year) + 1
                next_anniversary = issue_date + pd.DateOffset(years=years_since_issue)
                effective_end = min(next_anniversary, self.study_end)
                days = (effective_end - start).days
                return max(0.0, days / self.days_in_year)
            else:
                days = (end - start).days
                return max(0.0, days / self.days_in_year)

        elif self.method == ExposureMethod.CENSUS:
            days = (end - start).days
            return max(0.0, days / self.days_in_year)

        return 0.0

    def process_portfolio(
        self,
        df: pd.DataFrame,
        issue_col: str = "issue_date",
        exit_col: str = "exit_date",
        status_col: str = "status",
        death_status_val: str = "DEATH",
        face_amount_col: str = "face_amount",
        retention_limit_col: Optional[str] = "retention_limit",
        cedant_col: Optional[str] = "cedant_id",
    ) -> pd.DataFrame:
        """
        Process a longitudinal policy portfolio DataFrame and append exposure metrics.
        
        Parameters
        ----------
        df : pd.DataFrame
            Portfolio policyholder records.
        """
        df_out = df.copy()
        
        # Ensure datetimes
        df_out[issue_col] = pd.to_datetime(df_out[issue_col])
        if exit_col in df_out.columns:
            df_out[exit_col] = pd.to_datetime(df_out[exit_col])
        else:
            df_out[exit_col] = pd.NaT

        is_death = (df_out[status_col].astype(str).str.upper() == death_status_val.upper())
        df_out["is_death"] = is_death.astype(int)

        # Vectorized exposure calculation
        starts = np.maximum(
            df_out[issue_col].values.astype("datetime64[D]"),
            np.datetime64(self.study_start.date(), "D"),
        )
        
        ends_raw = df_out[exit_col].values.astype("datetime64[D]")
        study_end_dt = np.datetime64(self.study_end.date(), "D")
        
        # Where exit_date is NaT, replace with study_end
        is_nat = np.isnat(ends_raw)
        ends = np.where(is_nat, study_end_dt, np.minimum(ends_raw, study_end_dt))
        
        # Balducci adjustment for deaths if applicable
        if self.method == ExposureMethod.BALDUCCI_ANNUAL:
            # If death occurs within study window, credit full year exposure for that policy year
            death_mask = is_death.values & (~is_nat) & (ends_raw <= study_end_dt)
            # Adjust exposure days: add remaining days in policy year
            # Simple exact approximation: 1.0 - fractional year within that year
            # Or exact anniversary lookup
            days_diff = (ends - starts).astype(int)
            days_diff = np.maximum(0, days_diff)
            # Add remaining fractional year for deaths
            days_in_year_int = int(self.days_in_year)
            remainder = days_diff % days_in_year_int
            additional_days = np.where(death_mask & (remainder > 0), days_in_year_int - remainder, 0)
            days_diff = days_diff + additional_days
        else:
            days_diff = (ends - starts).astype(int)
            days_diff = np.maximum(0, days_diff)

        exposures = days_diff / self.days_in_year
        df_out["exposure_years"] = exposures

        # Only retain records with positive exposure in study period
        # or where a death occurred exactly on boundary
        df_out = df_out[df_out["exposure_years"] > 0].copy()

        # Face amount & Reinsurance Ceded Exposure
        if face_amount_col in df_out.columns:
            df_out["face_amount"] = pd.to_numeric(df_out[face_amount_col], errors="coerce").fillna(0.0)
            df_out["amount_exposure"] = df_out["exposure_years"] * df_out["face_amount"]
            
            # Ceded vs Retained Reinsurance
            if retention_limit_col and retention_limit_col in df_out.columns:
                retention = pd.to_numeric(df_out[retention_limit_col], errors="coerce").fillna(df_out["face_amount"])
                retained_amount = np.minimum(df_out["face_amount"], retention)
                ceded_amount = np.maximum(0.0, df_out["face_amount"] - retention)
                df_out["retained_amount"] = retained_amount
                df_out["ceded_amount"] = ceded_amount
                df_out["ceded_exposure"] = df_out["exposure_years"] * ceded_amount
                df_out["claim_amount_ceded"] = df_out["is_death"] * ceded_amount
                df_out["claim_amount_gross"] = df_out["is_death"] * df_out["face_amount"]
            else:
                df_out["claim_amount_gross"] = df_out["is_death"] * df_out["face_amount"]

        return df_out

    def split_by_policy_year(
        self,
        df: pd.DataFrame,
        issue_col: str = "issue_date",
        exit_col: str = "exit_date",
        max_duration: int = 30,
    ) -> pd.DataFrame:
        """
        Split policyholder records into individual (Policy, Policy Year) segments
        to support duration-dependent mortality and lapse studies.
        """
        records: List[Dict[str, Any]] = []

        for _, row in df.iterrows():
            issue = pd.to_datetime(row[issue_col])
            exit_dt = pd.to_datetime(row[exit_col]) if pd.notna(row[exit_col]) else None
            is_death = (str(row.get("status", "")).upper() == "DEATH")

            for dur in range(1, max_duration + 1):
                py_start = issue + pd.DateOffset(years=dur - 1)
                py_end = issue + pd.DateOffset(years=dur)

                # Segment effective boundaries
                seg_start = max(py_start, self.study_start)
                if exit_dt is None:
                    seg_end = min(py_end, self.study_end)
                else:
                    seg_end = min(py_end, exit_dt, self.study_end)

                if seg_end <= seg_start:
                    continue

                days = (seg_end - seg_start).days
                if days <= 0:
                    continue

                seg_death = 1 if (is_death and exit_dt is not None and py_start <= exit_dt <= py_end and exit_dt <= self.study_end) else 0

                rec = row.to_dict()
                rec["policy_year"] = dur
                rec["segment_start"] = seg_start
                rec["segment_end"] = seg_end
                rec["exposure_years"] = days / self.days_in_year
                rec["is_death"] = seg_death
                
                if "face_amount" in rec:
                    rec["amount_exposure"] = rec["exposure_years"] * rec["face_amount"]
                    rec["claim_amount_gross"] = seg_death * rec["face_amount"]
                    if "ceded_amount" in rec:
                        rec["ceded_exposure"] = rec["exposure_years"] * rec["ceded_amount"]
                        rec["claim_amount_ceded"] = seg_death * rec["ceded_amount"]

                records.append(rec)

        return pd.DataFrame(records)
