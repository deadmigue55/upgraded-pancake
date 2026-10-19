"""
Actuarial Reinsurance Analytics CLI
===================================

Command-line interface for running reinsurance experience studies,
credibility models, treaty layering, and stochastic capital simulation.
"""

from __future__ import annotations
import argparse
import os
import sys
import numpy as np
import pandas as pd

from reinsurance_analytics.core.exposure import ExposureEngine, ExposureMethod
from reinsurance_analytics.core.mortality_tables import SOAVBTBenchmark
from reinsurance_analytics.core.credibility import BuhlmannStraubCredibility, LimitedFluctuationCredibility
from reinsurance_analytics.life.experience_study import LifeExperienceStudy
from reinsurance_analytics.life.glm_modeling import ActuarialGLMExperience, SurvivalExperienceAnalyzer
from reinsurance_analytics.nonlife.distributions import LossDistributionFitter
from reinsurance_analytics.nonlife.loss_experience import TreatyLossExperienceStudy
from reinsurance_analytics.treaty.structures import ExcessOfLossTreaty, QuotaShareTreaty, ReinsuranceProgram
from reinsurance_analytics.simulation.collective_risk import CollectiveRiskSimulator
from reinsurance_analytics.simulation.risk_metrics import ActuarialRiskMetrics
from reinsurance_analytics.reporting.visualizer import ActuarialVisualizer
from reinsurance_analytics.reporting.report_builder import ActuarialReportBuilder
from reinsurance_analytics.data.generator import ReinsuranceDataGenerator


def run_full_analysis(output_dir: str = "output", policies: int = 15000, trials: int = 10000) -> None:
    """Execute end-to-end actuarial reinsurance experience study & modeling."""
    print("================================================================================")
    print("   ACTUARIAL REINSURANCE ANALYTICS: EXPERIENCE STUDY & RISK MODELING   ")
    print("================================================================================")
    
    os.makedirs(output_dir, exist_ok=True)
    fig_dir = os.path.join(output_dir, "figures")
    rep_dir = os.path.join(output_dir, "reports")
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(rep_dir, exist_ok=True)

    # 1. Synthesize Longitudinal Reinsurance Portfolio
    print(f"\n[1/6] Synthesizing {policies:,} policyholder life reinsurance treaty portfolio...")
    generator = ReinsuranceDataGenerator(seed=123)
    raw_df = generator.generate_life_portfolio(num_policies=policies, start_year=2018, study_end_year=2023)
    print(f"      Synthesized {len(raw_df):,} policy records across 4 cedants.")

    # 2. Exposure & Expected Mortality Calculation
    print("\n[2/6] Computing actuarial continuous exposures and SOA VBT expected basis...")
    engine = ExposureEngine(study_start="2018-01-01", study_end="2023-12-31", method=ExposureMethod.EXACT_CONTINUOUS)
    portfolio_exposed = engine.process_portfolio(raw_df)
    
    benchmark = SOAVBTBenchmark()
    portfolio_modeled = benchmark.attach_expected_rates(portfolio_exposed)
    total_exposure = portfolio_modeled["exposure_years"].sum()
    total_actual_deaths = portfolio_modeled["is_death"].sum()
    total_expected_deaths = portfolio_modeled["expected_claims_count"].sum()
    print(f"      Total Exposure: {total_exposure:,.1f} life-years")
    print(f"      Actual Deaths: {total_actual_deaths} | Expected Deaths: {total_expected_deaths:,.1f}")

    # 3. Life Experience Study & Credibility
    print("\n[3/6] Conducting multi-dimensional Life Experience Study (A/E) & Credibility...")
    # Age bands
    portfolio_modeled["age_band"] = pd.cut(
        portfolio_modeled["attained_age"],
        bins=[0, 35, 45, 55, 65, 100],
        labels=["<35", "35-44", "45-54", "55-64", "65+"],
    )

    study = LifeExperienceStudy(confidence_level=0.95)
    study_result = study.analyze(
        portfolio_modeled,
        group_cols=["age_band", "smoker"],
        actual_count_col="is_death",
        expected_count_col="expected_claims_count",
        exposure_col="exposure_years",
        actual_amount_col="claim_amount_gross",
        expected_amount_col="expected_claims_amount",
    )
    ae_summary = study_result.summary_table
    print(f"      Overall A/E (Count): {study_result.ae_ratio_count * 100:.2f}% (95% CI: [{study_result.ae_count_ci_lower*100:.2f}%, {study_result.ae_count_ci_upper*100:.2f}%])")
    print(f"      Overall Credibility Factor Z: {study_result.overall_credibility_z:.3f}")
    print(f"      Credibility-Adjusted A/E Basis: {study_result.credibility_adjusted_ae * 100:.2f}%")

    # Bühlmann-Straub multi-cedant credibility
    print("      Fitting Bühlmann-Straub Empirical Bayes credibility across cedants...")
    # Compute annual loss ratios per cedant
    portfolio_modeled["issue_year"] = pd.to_datetime(portfolio_modeled["issue_date"]).dt.year
    cedant_panel = portfolio_modeled.groupby(["cedant_id", "issue_year"]).agg({
        "is_death": "sum",
        "expected_claims_count": "sum",
        "exposure_years": "sum",
    }).reset_index()
    cedant_panel["loss_rate"] = cedant_panel["is_death"] / cedant_panel["exposure_years"]

    bs_cred = BuhlmannStraubCredibility()
    bs_fit = bs_cred.fit(cedant_panel, group_col="cedant_id", loss_ratio_col="loss_rate", exposure_col="exposure_years")
    print(f"      Bühlmann constant k*: {bs_fit['buhlmann_constant_k']:,.1f} | Collective Mean: {bs_fit['collective_mean_mu']:.4f}")

    # 4. Actuarial GLM Mortality Relativities
    print("\n[4/6] Calibrating Actuarial GLM with log-exposure offset...")
    glm = ActuarialGLMExperience(family="poisson")
    glm_res = glm.fit(portfolio_modeled, formula="is_death ~ C(gender) + C(smoker) + C(underwriting_class)", exposure_col="exposure_years")
    print("      GLM Relativities (Multipliers exp(beta)):")
    for idx, row in glm_res["relativities"].iterrows():
        print(f"        - {idx}: {row['Relativity_exp_beta']:.3f} (p-value: {row['p_value']:.4f})")

    # 5. Non-Life Treaty Loss Experience & Collective Risk Simulation
    print(f"\n[5/6] Simulating Treaty Loss Experience & {trials:,} Monte Carlo Collective Risk trials...")
    claims_df, prems_df = generator.generate_treaty_claims_history(num_years=10, start_year=2014)
    loss_fitter = LossDistributionFitter(claims_df["gross_loss"].values)
    fit_table = loss_fitter.fit_all()
    best_dist_name, best_dist = loss_fitter.get_best_model()
    print(f"      Best-fitting loss severity distribution: {best_dist_name}")

    # Structure 3-layer Reinsurance Tower
    program = ReinsuranceProgram([
        ExcessOfLossTreaty(attachment=500000.0, limit=1000000.0, rate_on_line=0.12, name="Working_XL_1M_xs_500k"),
        ExcessOfLossTreaty(attachment=1500000.0, limit=3500000.0, rate_on_line=0.06, name="Mezzanine_XL_3.5M_xs_1.5M"),
        ExcessOfLossTreaty(attachment=5000000.0, limit=10000000.0, rate_on_line=0.025, name="Catastrophe_XL_10M_xs_5M"),
    ])

    sim = CollectiveRiskSimulator(severity_dist=best_dist, frequency_type="poisson", poisson_lambda=35.0, random_state=42)
    sim_res = sim.simulate(num_trials=trials, treaty_program=program)

    capital_relief = ActuarialRiskMetrics.calculate_capital_relief(
        gross_losses=sim_res.gross_aggregate_losses,
        net_losses=sim_res.net_aggregate_losses,
        alpha=0.995,
    )
    print(f"      Gross 99.5% VaR (1-in-200yr): ${capital_relief.gross_var_995:,.2f}")
    print(f"      Net Retained 99.5% VaR:        ${capital_relief.net_var_995:,.2f}")
    print(f"      Solvency II SCR Relief:        ${capital_relief.capital_relief_amount:,.2f} ({capital_relief.capital_relief_percentage:.1f}%)")

    # 6. Generate Figures & Executive Actuarial Report
    print("\n[6/6] Generating publication-quality charts and Actuarial Experience Report...")
    fig_ae = os.path.join(fig_dir, "mortality_ae_experience.png")
    fig_aep = os.path.join(fig_dir, "reinsurance_aep_curve.png")
    fig_cred = os.path.join(fig_dir, "credibility_convergence.png")

    ActuarialVisualizer.plot_ae_experience(ae_summary, x_col="age_band", save_path=fig_ae)
    ActuarialVisualizer.plot_exceedance_probability(sim_res.gross_aggregate_losses, sim_res.net_aggregate_losses, save_path=fig_aep)
    ActuarialVisualizer.plot_credibility_convergence(save_path=fig_cred)
    print(f"      Saved charts to: {fig_dir}")

    # Build reports
    md_report_file = os.path.join(rep_dir, "reinsurance_experience_report.md")
    html_report_file = os.path.join(rep_dir, "reinsurance_experience_report.html")

    builder = ActuarialReportBuilder()
    md_content = builder.build_markdown_report(
        life_study_dict=study_result.to_dict(),
        ae_table=ae_summary,
        credibility_dict=bs_fit,
        capital_relief_dict=capital_relief.to_dict(),
        glm_relativities=glm_res["relativities"],
        output_path=md_report_file,
    )
    builder.build_html_report(markdown_content=md_content, output_path=html_report_file)
    print(f"      Saved Markdown report to: {md_report_file}")
    print(f"      Saved HTML report to:     {html_report_file}")

    print("\n================================================================================")
    print("   ACTUARIAL EXPERIENCE STUDY COMPLETED SUCCESSFULLY!   ")
    print("================================================================================")


def main():
    parser = argparse.ArgumentParser(
        prog="reinsurx",
        description="Actuarial Reinsurance Experience Analysis and Risk Modeling CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Full analysis
    sub_full = subparsers.add_parser("full-analysis", help="Run full end-to-end actuarial experience analysis")
    sub_full.add_argument("--output", default="output", help="Directory to save figures and reports")
    sub_full.add_argument("--policies", type=int, default=15000, help="Number of policy records to simulate")
    sub_full.add_argument("--trials", type=int, default=10000, help="Number of Monte Carlo simulation trials")

    # Run study only
    sub_study = subparsers.add_parser("run-study", help="Run life mortality & lapse experience study")
    sub_study.add_argument("--policies", type=int, default=10000)

    # Run simulation only
    sub_sim = subparsers.add_parser("run-simulation", help="Run stochastic reinsurance treaty simulation")
    sub_sim.add_argument("--trials", type=int, default=5000)

    args = parser.parse_args()

    if args.command == "full-analysis" or args.command is None:
        out_dir = getattr(args, "output", "output")
        pols = getattr(args, "policies", 15000)
        trls = getattr(args, "trials", 10000)
        run_full_analysis(output_dir=out_dir, policies=pols, trials=trls)
    elif args.command == "run-study":
        run_full_analysis(policies=args.policies, trials=1000)
    elif args.command == "run-simulation":
        run_full_analysis(policies=5000, trials=args.trials)


if __name__ == "__main__":
    main()
