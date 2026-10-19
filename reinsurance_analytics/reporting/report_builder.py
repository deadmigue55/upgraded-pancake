"""
Actuarial Experience Study Report Builder
=========================================

Generates executive and technical reinsurance experience reports
in Markdown and HTML formats with embedded actuarial tables and summaries.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import os
import pandas as pd


class ActuarialReportBuilder:
    """
    Assembles comprehensive actuarial experience study reports.
    """

    def __init__(self, title: str = "Reinsurance Actuarial Experience Study & Treaty Risk Report"):
        self.title = title

    @staticmethod
    def _df_to_markdown(df: pd.DataFrame, include_index: bool = False) -> str:
        try:
            return df.to_markdown(index=include_index)
        except Exception:
            data = df.reset_index() if include_index else df.copy()
            cols = [str(c) for c in data.columns]
            lines = ["| " + " | ".join(cols) + " |"]
            lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
            for _, row in data.iterrows():
                vals = [str(v) for v in row.values]
                lines.append("| " + " | ".join(vals) + " |")
            return "\n".join(lines)

    def build_markdown_report(
        self,
        life_study_dict: Dict[str, Any],
        ae_table: pd.DataFrame,
        credibility_dict: Dict[str, Any],
        capital_relief_dict: Dict[str, Any],
        burning_cost_df: Optional[pd.DataFrame] = None,
        glm_relativities: Optional[pd.DataFrame] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate full Markdown report.
        """
        md = []
        md.append(f"# {self.title}\n")
        md.append("> **Prepared by:** Quantitative Actuarial & Reinsurance Analytics Framework\n")
        md.append("> **Standard Frameworks:** SOA Valuation Basic Table (VBT) Benchmark, Limited Fluctuation & Bühlmann-Straub Credibility, Extreme Value Theory, Solvency II SCR Model.\n")
        md.append("---\n")

        # 1. Executive Summary
        md.append("## 1. Executive Actuarial Summary\n")
        md.append(f"- **Total Portfolio Exposure:** {life_study_dict.get('total_exposure_years', 0):,.1f} life-years")
        md.append(f"- **Actual Claims Count:** {life_study_dict.get('actual_claims_count', 0):,d}")
        md.append(f"- **Expected Claims Count (SOA Baseline):** {life_study_dict.get('expected_claims_count', 0):,.1f}")
        ae_cnt = life_study_dict.get('ae_ratio_count', 0)
        ci = life_study_dict.get('ae_count_95ci', [0, 0])
        md.append(f"- **Overall Portfolio A/E (Count):** **{ae_cnt * 100:.2f}%** (95% Poisson CI: [{ci[0]*100:.2f}%, {ci[1]*100:.2f}%])")
        ae_amt = life_study_dict.get('ae_ratio_amount', 0)
        md.append(f"- **Overall Portfolio A/E (Amount):** **{ae_amt * 100:.2f}%**")
        z = life_study_dict.get('overall_credibility_z', 0)
        cred_ae = life_study_dict.get('credibility_adjusted_ae', 0)
        md.append(f"- **Overall Credibility Factor ($Z$):** **{z:.2f}** $\\implies$ **Credibility-Weighted A/E Basis: {cred_ae * 100:.2f}%**")
        chi2_p = life_study_dict.get('chi_square_p_value', 1.0)
        md.append(f"- **Goodness-of-Fit Pearson $\\chi^2$ p-value:** {chi2_p:.5f}\n")

        # 2. Detailed Experience Study Table
        md.append("## 2. Demographic & Cohort Experience Study\n")
        md.append("Below is the detailed stratification of Actual vs Expected mortality by cohort cell:\n")
        # Format table
        display_df = ae_table.copy()
        numeric_cols = display_df.select_dtypes(include=["float", "int"]).columns
        for c in numeric_cols:
            if "ae" in c or "credibility" in c or "Z" in c:
                display_df[c] = display_df[c].apply(lambda v: f"{v:.4f}" if pd.notna(v) else "")
            elif "exposure" in c or "claims" in c:
                display_df[c] = display_df[c].apply(lambda v: f"{v:,.1f}" if pd.notna(v) else "")
            elif "amount" in c:
                display_df[c] = display_df[c].apply(lambda v: f"${v:,.0f}" if pd.notna(v) else "")
        md.append(self._df_to_markdown(display_df, include_index=False))
        md.append("\n")

        # 3. Credibility Analysis
        md.append("## 3. Actuarial Credibility Evaluation\n")
        md.append("### Bühlmann-Straub Empirical Bayes Variance Components\n")
        md.append(f"- **Expected Process Variance (EPV / $s^2$):** `{credibility_dict.get('epv_s2', 0):.6e}`")
        md.append(f"- **Variance of Hypothetical Means (VHM / $a$):** `{credibility_dict.get('vhm_a', 0):.6e}`")
        k_val = credibility_dict.get('buhlmann_constant_k', 0)
        md.append(f"- **Bühlmann Parameter ($k^* = s^2 / a$):** `{k_val:,.1f}`")
        md.append(f"- **Portfolio Collective Mean ($\\mu$):** `{credibility_dict.get('collective_mean_mu', 0):.4f}`\n")

        # 4. GLM Multiplicative Relativities
        if glm_relativities is not None and not glm_relativities.empty:
            md.append("## 4. Actuarial GLM Experience Rating Multipliers\n")
            md.append("Poisson GLM with $\\log(\\text{Exposure})$ offset parameter estimates and multiplicative risk relativities:\n")
            md.append(self._df_to_markdown(glm_relativities, include_index=True))
            md.append("\n")

        # 5. Non-Life Treaty Burning Cost Experience
        if burning_cost_df is not None and not burning_cost_df.empty:
            md.append("## 5. Non-Life / Property & Casualty Treaty Loss Experience\n")
            md.append("Historical indexed burning cost experience for excess-of-loss layer:\n")
            md.append(self._df_to_markdown(burning_cost_df, include_index=False))
            md.append("\n")

        # 6. Reinsurance Capital Relief & Stochastic Solvency Analysis
        md.append("## 6. Reinsurance Treaty Risk Transfer & Capital Relief (Solvency II / RBC)\n")
        md.append("Stochastic simulation evaluation of 1-in-200 year (99.5%) solvency capital relief:\n")
        md.append(f"- **Gross Portfolio Expected Loss:** ${capital_relief_dict.get('gross_expected_loss', 0):,.2f}")
        md.append(f"- **Net Retained Expected Loss:** ${capital_relief_dict.get('net_expected_loss', 0):,.2f}")
        md.append(f"- **Gross 99.5% VaR (1-in-200 Year Loss):** ${capital_relief_dict.get('gross_var_995', 0):,.2f}")
        md.append(f"- **Net Retained 99.5% VaR:** ${capital_relief_dict.get('net_var_995', 0):,.2f}")
        md.append(f"- **Gross 99.5% TVaR (Expected Shortfall):** ${capital_relief_dict.get('gross_tvar_995', 0):,.2f}")
        md.append(f"- **Net Retained 99.5% TVaR:** ${capital_relief_dict.get('net_tvar_995', 0):,.2f}")
        md.append(f"- **Gross Required Solvency Capital:** ${capital_relief_dict.get('gross_required_capital_995', 0):,.2f}")
        md.append(f"- **Net Required Solvency Capital:** ${capital_relief_dict.get('net_required_capital_995', 0):,.2f}")
        relief_amt = capital_relief_dict.get('capital_relief_amount', 0)
        relief_pct = capital_relief_dict.get('capital_relief_percentage', 0)
        md.append(f"- **Capital Relief Conferred by Reinsurance:** **${relief_amt:,.2f} ({relief_pct:.1f}% SCR Reduction)**\n")

        # 7. Actuarial Recommendations
        md.append("## 7. Actuarial Recommendations & Underwriting Conclusions\n")
        md.append("1. **Mortality Basis Revision:** Given credibility-weighted A/E of "
                  f"{cred_ae*100:.1f}%, adjust treaty base table assumptions accordingly.\n"
                  "2. **Layer Optimization:** The excess-of-loss reinsurance structure releases "
                  f"{relief_pct:.1f}% of 1-in-200 year underwriting risk capital, optimizing cedant solvency margins.\n"
                  "3. **Cedant Heterogeneity:** Empirical Bayes credibility demonstrates significant between-cedant variation ($a > 0$), warranting treaty-specific experience rating rather than flat pooling.")

        report_content = "\n".join(md)

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)

        return report_content

    def build_html_report(
        self,
        markdown_content: str,
        output_path: Optional[str] = None,
    ) -> str:
        """Convert markdown to a polished, professional HTML actuarial report."""
        import html
        lines = markdown_content.split("\n")
        html_body = []
        in_table = False
        table_rows = []

        for line in lines:
            line_str = line.strip()
            if line_str.startswith("# "):
                html_body.append(f"<h1>{html.escape(line_str[2:])}</h1>")
            elif line_str.startswith("## "):
                html_body.append(f"<h2>{html.escape(line_str[3:])}</h2>")
            elif line_str.startswith("### "):
                html_body.append(f"<h3>{html.escape(line_str[4:])}</h3>")
            elif line_str.startswith("> "):
                html_body.append(f"<blockquote>{html.escape(line_str[2:])}</blockquote>")
            elif line_str.startswith("- "):
                html_body.append(f"<li>{line_str[2:]}</li>")
            elif line_str.startswith("|"):
                if not in_table:
                    in_table = True
                    table_rows = []
                table_rows.append(line_str)
            else:
                if in_table:
                    # Flush table
                    in_table = False
                    html_body.append(self._format_html_table(table_rows))
                    table_rows = []
                if line_str:
                    html_body.append(f"<p>{line_str}</p>")

        if in_table and table_rows:
            html_body.append(self._format_html_table(table_rows))

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self.title}</title>
<style>
  :root {{
    --primary: #0f172a;
    --accent: #0284c7;
    --accent-light: #e0f2fe;
    --secondary: #0d9488;
    --bg-page: #f8fafc;
    --card-bg: #ffffff;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --success: #16a34a;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.65;
    color: var(--text-main);
    background-color: var(--bg-page);
    margin: 0;
    padding: 30px 20px;
  }}
  .container {{
    max-width: 1080px;
    margin: 0 auto;
    background: var(--card-bg);
    padding: 40px 50px;
    border-radius: 14px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    border: 1px solid var(--border-color);
  }}
  h1 {{
    color: #ffffff;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    padding: 24px 28px;
    border-radius: 10px;
    font-size: 26px;
    font-weight: 700;
    margin: -10px -10px 30px -10px;
    box-shadow: 0 4px 15px rgba(15, 23, 42, 0.15);
  }}
  h2 {{
    color: #0f172a;
    margin-top: 36px;
    margin-bottom: 14px;
    border-bottom: 2px solid var(--accent);
    padding-bottom: 8px;
    font-size: 20px;
  }}
  h3 {{
    color: #334155;
    font-size: 16px;
    margin-top: 22px;
  }}
  blockquote {{
    background: var(--accent-light);
    border-left: 5px solid var(--accent);
    margin: 15px 0;
    padding: 12px 18px;
    border-radius: 0 8px 8px 0;
    color: #0369a1;
    font-size: 14px;
  }}
  table {{
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    margin: 22px 0;
    font-size: 13.5px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
  }}
  th, td {{
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
  }}
  th {{
    background-color: #0f172a;
    color: #ffffff;
    font-weight: 600;
    letter-spacing: 0.3px;
  }}
  tr:last-child td {{
    border-bottom: none;
  }}
  tr:nth-child(even) {{
    background-color: #f8fafc;
  }}
  tr:hover {{
    background-color: #f1f5f9;
  }}
  li {{
    margin-bottom: 8px;
    color: #334155;
  }}
  code {{
    background: #f1f5f9;
    color: #be185d;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    border: 1px solid #e2e8f0;
  }}
  strong {{
    color: #0f172a;
  }}
  p {{
    margin: 12px 0;
  }}
</style>
</head>
<body>
<div class="container">
{"".join(html_body)}
</div>
</body>
</html>"""

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_html)

        return full_html

    @staticmethod
    def _format_html_table(rows: list[str]) -> str:
        if not rows:
            return ""
        html_out = ["<table>"]
        # Header row
        headers = [c.strip() for c in rows[0].split("|")[1:-1]]
        html_out.append("<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>")
        html_out.append("<tbody>")
        for r in rows[2:]:  # skip separator row
            cells = [c.strip() for c in r.split("|")[1:-1]]
            html_out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        html_out.append("</tbody></table>")
        return "".join(html_out)
