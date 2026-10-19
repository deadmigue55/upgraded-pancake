"""
Actuarial Data Visualizer
=========================

Generates publication-quality actuarial charts for experience analysis:
- Actual-to-Expected (A/E) ratios with Garwood Poisson 95% Confidence Intervals
- Kaplan-Meier survival curves with Greenwood confidence bands
- Heavy-tailed severity distribution fits & Q-Q diagnostics
- Aggregate Exceedance Probability (AEP) curves (Gross vs Net Reinsurance)
- Credibility transition curves (Z factor vs claim count)
- Treaty layer burning cost historical trend
"""

from __future__ import annotations
from typing import Optional, List
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server/CLI execution
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


class ActuarialVisualizer:
    """
    Renders actuarial diagnostic graphs for reinsurance experience studies.
    """

    @staticmethod
    def plot_ae_experience(
        ae_df: pd.DataFrame,
        x_col: str,
        title: str = "Actual-to-Expected (A/E) Mortality Experience Study",
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Plot A/E ratio points with exact Poisson 95% error bars and 100% benchmark line.
        """
        fig, ax1 = plt.subplots(figsize=(10, 6), dpi=300)

        x_vals = np.arange(len(ae_df))
        labels = [str(x) for x in ae_df[x_col]]

        ae = ae_df["ae_ratio_count"].values
        ci_low = ae_df["ae_ci_lower"].values
        ci_high = ae_df["ae_ci_upper"].values
        err_low = np.maximum(0, ae - ci_low)
        err_high = np.maximum(0, ci_high - ae)

        # Plot 100% benchmark reference line
        ax1.axhline(1.0, color="#d9534f", linestyle="--", linewidth=1.5, label="Expected Basis (100% SOA VBT)")

        # Error bars for A/E
        ax1.errorbar(
            x_vals,
            ae,
            yerr=[err_low, err_high],
            fmt="o-",
            color="#1b4965",
            ecolor="#62b6cb",
            elinewidth=2,
            capsize=4,
            capthick=1.5,
            markersize=7,
            label="Observed A/E (Count) with 95% Poisson CI",
        )

        if "credibility_adjusted_ae" in ae_df.columns:
            ax1.plot(
                x_vals,
                ae_df["credibility_adjusted_ae"].values,
                "s--",
                color="#f39c12",
                markersize=6,
                label="Credibility-Adjusted A/E Basis",
            )

        ax1.set_xlabel(x_col.replace("_", " ").title(), fontsize=12, fontweight="bold")
        ax1.set_ylabel("Actual / Expected Ratio (A/E)", fontsize=12, fontweight="bold")
        ax1.set_xticks(x_vals)
        ax1.set_xticklabels(labels, rotation=45, ha="right")
        ax1.set_title(title, fontsize=14, fontweight="bold", pad=15)
        ax1.grid(True, linestyle=":", alpha=0.6)

        # Exposure secondary axis
        if "exposure_years" in ae_df.columns:
            ax2 = ax1.twinx()
            ax2.bar(x_vals, ae_df["exposure_years"].values, alpha=0.15, color="#2b2d42", width=0.4, label="Exposure (Life-Years)")
            ax2.set_ylabel("Exposure (Years)", fontsize=11, color="#2b2d42")
            ax2.tick_params(axis="y", labelcolor="#2b2d42")

        # Combine legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        if "exposure_years" in ae_df.columns:
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", framealpha=0.9)
        else:
            ax1.legend(loc="upper right", framealpha=0.9)

        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, bbox_inches="tight")
        return fig

    @staticmethod
    def plot_kaplan_meier_curves(
        curves: List[Tuple[str, pd.DataFrame]],
        title: str = "Kaplan-Meier Survival Function by Risk Cohort",
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Plot multiple Kaplan-Meier survival curves with Greenwood confidence ribbons.
        """
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
        colors = ["#1b4965", "#d9534f", "#2a9d8f", "#e76f51", "#7209b7"]

        for idx, (label, df_km) in enumerate(curves):
            c = colors[idx % len(colors)]
            ax.step(df_km["time"], df_km["survival_prob"], where="post", color=c, linewidth=2, label=f"{label} S(t)")
            ax.fill_between(df_km["time"], df_km["ci_lower"], df_km["ci_upper"], color=c, alpha=0.15, step="post")

        ax.set_xlabel("Policy Duration (Years)", fontsize=12, fontweight="bold")
        ax.set_ylabel("Survival Probability S(t)", fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
        ax.set_ylim(0.80, 1.005)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="lower left", framealpha=0.9)

        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, bbox_inches="tight")
        return fig

    @staticmethod
    def plot_exceedance_probability(
        gross_losses: np.ndarray,
        net_losses: np.ndarray,
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """
        Plot Aggregate Exceedance Probability (AEP) curves on log-log scale.
        """
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

        # Gross AEP
        g_sorted = np.sort(gross_losses)
        n = len(g_sorted)
        p_exceed = 1.0 - (np.arange(1, n + 1) / (n + 1.0))
        return_period = 1.0 / p_exceed

        # Net AEP
        net_sorted = np.sort(net_losses)

        # Plot curves
        ax.plot(return_period, g_sorted / 1e6, color="#d9534f", linewidth=2.5, label="Gross Portfolio Loss")
        ax.plot(return_period, net_sorted / 1e6, color="#1b4965", linewidth=2.5, linestyle="--", label="Net Retained Loss (After Reinsurance)")

        # Highlight Solvency II 1-in-200 year point
        idx_200 = np.searchsorted(return_period, 200.0)
        if idx_200 < n:
            g_200 = g_sorted[idx_200] / 1e6
            net_200 = net_sorted[idx_200] / 1e6
            ax.axvline(200.0, color="#2b2d42", linestyle=":", linewidth=1.5, label="1-in-200 Year Benchmark (99.5%)")
            ax.scatter([200.0], [g_200], color="#d9534f", s=60, zorder=5)
            ax.scatter([200.0], [net_200], color="#1b4965", s=60, zorder=5)
            ax.annotate(f"Gross: ${g_200:.1f}M", (200.0, g_200), textcoords="offset points", xytext=(-80, 5), fontweight="bold")
            ax.annotate(f"Net: ${net_200:.1f}M", (200.0, net_200), textcoords="offset points", xytext=(-80, -15), fontweight="bold")

        ax.set_xscale("log")
        ax.set_xlabel("Return Period (Years)", fontsize=12, fontweight="bold")
        ax.set_ylabel("Aggregate Loss ($ Millions)", fontsize=12, fontweight="bold")
        ax.set_title("Aggregate Exceedance Probability (AEP) Curve & Reinsurance Relief", fontsize=14, fontweight="bold", pad=15)
        ax.grid(True, which="both", linestyle=":", alpha=0.6)
        ax.legend(loc="upper left", framealpha=0.9)

        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, bbox_inches="tight")
        return fig

    @staticmethod
    def plot_credibility_convergence(save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot classical limited fluctuation credibility factor Z vs claim count.
        """
        fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
        n = np.linspace(0, 2000, 500)

        # Pure Poisson (CV=0): n* = 1082
        z_poisson = np.minimum(1.0, np.sqrt(n / 1082.41))
        # Severity with CV=1.0: n* = 1082 * 2 = 2164
        z_cv1 = np.minimum(1.0, np.sqrt(n / 2164.82))
        # Severity with CV=2.0 (heavy-tailed): n* = 1082 * 5 = 5412
        z_cv2 = np.minimum(1.0, np.sqrt(n / 5412.0))

        ax.plot(n, z_poisson, label="Pure Poisson Claims (CV = 0, n* = 1,082)", color="#1b4965", linewidth=2)
        ax.plot(n, z_cv1, label="Compound Claims (CV = 1.0, n* = 2,165)", color="#2a9d8f", linewidth=2, linestyle="--")
        ax.plot(n, z_cv2, label="Heavy-Tailed Claims (CV = 2.0, n* = 5,412)", color="#e76f51", linewidth=2, linestyle=":")

        ax.axhline(1.0, color="#d9534f", linestyle="--", alpha=0.7, label="Full Credibility Standard (Z = 1.0)")
        ax.axvline(1082.41, color="#1b4965", linestyle=":", alpha=0.7)

        ax.set_xlabel("Number of Observed Claims (n)", fontsize=12, fontweight="bold")
        ax.set_ylabel("Credibility Factor (Z)", fontsize=12, fontweight="bold")
        ax.set_title("Limited Fluctuation Credibility Convergence (90% Conf / 5% Margin)", fontsize=13, fontweight="bold", pad=12)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="lower right", framealpha=0.9)

        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, bbox_inches="tight")
        return fig
