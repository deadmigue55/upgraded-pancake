"""
Actuarial Data Generator for Reinsurance Portfolios
===================================================

Synthesizes realistic longitudinal datasets for:
1. Life & Health Treaty Experience Studies (Mortality, Lapses, Cedant Portfolios)
2. Property & Casualty / Excess of Loss Treaty Claims (Heavy-tailed shock losses)
"""

from __future__ import annotations
from typing import Tuple, Optional
import numpy as np
import pandas as pd


class ReinsuranceDataGenerator:
    """
    Generates synthetic, actuarially realistic reinsurance portfolios.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate_life_portfolio(
        self,
        num_policies: int = 25000,
        start_year: int = 2018,
        study_end_year: int = 2023,
    ) -> pd.DataFrame:
        """
        Generate a multi-cedant longitudinal individual life reinsurance portfolio.
        """
        policy_ids = [f"POL-{i+1:06d}" for i in range(num_policies)]
        
        # Cedants with differing underlying risk baselines (for Bühlmann-Straub credibility)
        cedants = ["CEDANT_APEX", "CEDANT_BEACON", "CEDANT_CREST", "CEDANT_DELTA"]
        cedant_probs = [0.35, 0.25, 0.25, 0.15]
        cedant_alloc = self.rng.choice(cedants, size=num_policies, p=cedant_probs)

        # Baseline age at issue ~ Normal(42, 11), clamped [20, 75]
        issue_ages = np.clip(np.round(self.rng.normal(42, 11, size=num_policies)).astype(int), 20, 75)

        # Gender: 55% M, 45% F
        genders = self.rng.choice(["M", "F"], size=num_policies, p=[0.55, 0.45])

        # Smoker status: 18% Smoker, 82% Non-Smoker
        smokers = self.rng.choice(["SM", "NS"], size=num_policies, p=[0.18, 0.82])

        # Underwriting class
        uw_classes = self.rng.choice(
            ["PREFERRED_PLUS", "PREFERRED", "STANDARD", "SUBSTANDARD"],
            size=num_policies,
            p=[0.20, 0.35, 0.35, 0.10],
        )

        # Face amounts: lognormal distribution centered ~$250,000, ranging to $5M
        raw_amounts = np.exp(self.rng.normal(12.3, 0.75, size=num_policies))
        face_amounts = np.clip(np.round(raw_amounts / 10000.0) * 10000.0, 50000.0, 5000000.0)

        # Cedant retention limits: typically $250k or $500k
        retention_limits = self.rng.choice([250000.0, 500000.0], size=num_policies, p=[0.60, 0.40])

        # Issue dates distributed between start_year-4 and study_end_year
        start_date = pd.Timestamp(f"{start_year - 4}-01-01")
        end_date = pd.Timestamp(f"{study_end_year}-12-31")
        total_days = (end_date - start_date).days
        random_days = self.rng.integers(0, total_days, size=num_policies)
        issue_dates = [start_date + pd.Timedelta(days=int(d)) for d in random_days]

        # Simulate events (death, lapse, active)
        records = []
        study_end_ts = pd.Timestamp(f"{study_end_year}-12-31")

        # Cedant-specific mortality multiplier
        cedant_relativities = {
            "CEDANT_APEX": 0.95,
            "CEDANT_BEACON": 1.05,
            "CEDANT_CREST": 1.18,
            "CEDANT_DELTA": 0.88,
        }

        for i in range(num_policies):
            issue_dt = issue_dates[i]
            age_at_issue = issue_ages[i]
            gender = genders[i]
            smoker = smokers[i]
            uw = uw_classes[i]
            cedant = cedant_alloc[i]
            face = face_amounts[i]
            retention = retention_limits[i]

            # Track policy evolution year by year
            curr_date = issue_dt
            curr_age = age_at_issue
            status = "ACTIVE"
            exit_dt = None

            dur = 1
            while curr_date < study_end_ts:
                # Annual mortality hazard using Gompertz law
                base_qx = 0.0003 + 0.000035 * (1.092 ** curr_age)
                if gender == "F":
                    base_qx *= 0.68
                if smoker == "SM":
                    base_qx *= 2.1
                if uw == "PREFERRED_PLUS":
                    base_qx *= 0.70
                elif uw == "PREFERRED":
                    base_qx *= 0.85
                elif uw == "SUBSTANDARD":
                    base_qx *= 1.80

                base_qx *= cedant_relativities[cedant]
                # Selection discount in early durations
                sel_factor = {1: 0.60, 2: 0.70, 3: 0.80, 4: 0.90}.get(dur, 1.0)
                qx = np.clip(base_qx * sel_factor, 0.0001, 0.999)

                # Duration lapse rate (high in year 1, lower later)
                lapse_rate = {1: 0.09, 2: 0.06, 3: 0.04}.get(dur, 0.025)

                # Draw uniform random
                u_death = self.rng.uniform(0.0, 1.0)
                u_lapse = self.rng.uniform(0.0, 1.0)

                if u_death < qx:
                    # Death occurred during this policy year
                    day_in_year = self.rng.integers(1, 365)
                    exit_dt = curr_date + pd.Timedelta(days=int(day_in_year))
                    status = "DEATH"
                    break
                elif u_lapse < lapse_rate:
                    # Lapse occurred
                    day_in_year = self.rng.integers(1, 365)
                    exit_dt = curr_date + pd.Timedelta(days=int(day_in_year))
                    status = "LAPSE"
                    break

                # Advance to next policy year
                curr_date += pd.Timedelta(days=365)
                curr_age += 1
                dur += 1

            records.append({
                "policy_id": policy_ids[i],
                "cedant_id": cedant,
                "issue_date": issue_dt,
                "age_at_issue": age_at_issue,
                "attained_age": curr_age,
                "gender": gender,
                "smoker": smoker,
                "underwriting_class": uw,
                "face_amount": face,
                "retention_limit": retention,
                "status": status,
                "exit_date": exit_dt,
            })

        return pd.DataFrame(records)

    def generate_treaty_claims_history(
        self,
        num_years: int = 10,
        start_year: int = 2014,
        mean_frequency: float = 35.0,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate multi-year historical ground-up treaty claims with heavy-tailed severity.
        """
        claims_list = []
        premiums_list = []

        base_premium = 50_000_000.0  # $50M subject earned premium

        for yr_idx in range(num_years):
            yr = start_year + yr_idx
            # Inflation of premium
            subj_prem = base_premium * ((1.0 + 0.04) ** yr_idx)
            premiums_list.append({"year": yr, "subject_premium": subj_prem})

            # Poisson claim count with slight random fluctuation
            n_claims = self.rng.poisson(mean_frequency * ((1.0 + 0.02) ** yr_idx))

            # Severity: 85% Lognormal attritional/moderate, 15% Pareto shock tail
            for c_idx in range(n_claims):
                is_shock = self.rng.uniform(0.0, 1.0) < 0.15
                if is_shock:
                    # Pareto heavy tail: alpha = 1.65, xm = $500,000
                    u = self.rng.uniform(0.00001, 0.99999)
                    loss_amt = 500000.0 / ((1.0 - u) ** (1.0 / 1.65))
                else:
                    # Lognormal: mu = 11.5 (~$100k), sigma = 1.0
                    loss_amt = np.exp(self.rng.normal(11.5, 1.0))

                # Random day in accident year
                day_of_year = self.rng.integers(1, 365)
                loss_date = pd.Timestamp(f"{yr}-01-01") + pd.Timedelta(days=int(day_of_year))

                claims_list.append({
                    "claim_id": f"CLM-{yr}-{c_idx+1:04d}",
                    "year": yr,
                    "loss_date": loss_date,
                    "gross_loss": round(float(loss_amt), 2),
                    "is_large_loss": int(is_shock or loss_amt > 1000000.0),
                })

        return pd.DataFrame(claims_list), pd.DataFrame(premiums_list)
