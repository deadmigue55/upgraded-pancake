# 📊 Empirical Results, Quantitative Benchmarks & Case Studies

This document provides a detailed breakdown of the empirical results, statistical findings, actuarial tables, capital relief calculations, and computational benchmarks produced by `reinsurance-analytics` on a production-scale simulated life and non-life reinsurance portfolio.

---

## 🏛️ Executive Summary & Key Actuarial Findings

An end-to-end experience analysis was conducted across a longitudinal portfolio of **15,000 policyholders** tracked over a 5-year observation window (2020–2024), generating **34,446.5 life-years of exposure**.

```
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│     PORTFOLIO EXPOSURE          │       OVERALL A/E (COUNT)       │    CREDIBILITY-WEIGHTED BASIS   │
│     34,446.5 Life-Years         │   103.79% (95% CI: 87.3%-122.5%)│       100.93% (Z = 0.24)        │
├─────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┤
│     GROSS 99.5% VaR (1-in-200)  │     NET RETAINED 99.5% VaR      │    SOLVENCY II CAPITAL RELIEF   │
│         $87,948,627.52          │         $48,078,627.34          │     $18,250,679.19 (37.1%)      │
└─────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┘
```

### Key Actuarial Insights:
1. **Unbiased Baseline Alignment:** The portfolio's overall actual-to-expected ratio is $103.79\%$, with the $95\%$ Garwood Poisson confidence interval $[87.31\%, 122.48\%]$ spanning $100\%$, indicating that aggregate mortality closely conforms to the underlying SOA 2015 Valuation Basic Table (VBT) baseline ($p = 0.113$).
2. **Amount-to-Count Skewness:** The dollar-weighted ratio ($\text{A/E}_{\text{amount}} = 121.42\%$) exceeds the count-based ratio ($\text{A/E}_{\text{count}} = 103.79\%$), signaling negative mortality selection concentrated in higher face-amount policy tiers.
3. **Substantial Capital Relief:** A multi-tier excess-of-loss reinsurance structure releases **37.1% of Underwriting Solvency Capital Requirement (SCR)** under the European Solvency II / NAIC RBC standard formula, freeing up **$18.25M** in regulatory surplus.

---

## 📈 Demographic & Cohort Experience Study

Below is the actuarial stratification table segmenting exposure, actual mortality, expected claims, Garwood confidence intervals, and credibility adjustments across attained age bands and smoking status:

| Age Band | Smoker Status | Exposure (Life-Years) | Actual Claims | Expected Claims | A/E (Count) | 95% Poisson CI (Lower) | 95% Poisson CI (Upper) | Actual Claims ($) | Expected Claims ($) | A/E (Amount) | Credibility Factor ($Z$) | Credibility A/E |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **< 35** | Non-Smoker | 3,498.4 | 4 | 2.2 | **183.96%** | 50.12% | 471.01% | $1,490,000 | $623,447 | **238.99%** | 0.044 | **103.73%** |
| **< 35** | Smoker | 713.4 | 0 | 0.9 | **0.00%** | 0.00% | 325.17% | $0 | $258,050 | **0.00%** | 0.000 | **100.00%** |
| **35 – 44** | Non-Smoker | 8,156.1 | 15 | 10.2 | **146.60%** | 82.05% | 241.79% | $4,810,000 | $2,958,179 | **162.60%** | 0.101 | **104.71%** |
| **35 – 44** | Smoker | 1,733.2 | 5 | 4.4 | **113.01%** | 36.69% | 263.73% | $2,970,000 | $1,385,939 | **214.30%** | 0.045 | **100.58%** |
| **45 – 54** | Non-Smoker | 9,518.9 | 31 | 24.2 | **128.06%** | 87.01% | 181.77% | $11,590,000 | $7,066,130 | **164.02%** | 0.097 | **102.71%** |
| **45 – 54** | Smoker | 2,099.3 | 9 | 10.9 | **82.73%** | 37.83% | 157.05% | $2,000,000 | $3,042,310 | **65.74%** | 0.074 | **98.73%** |
| **55 – 64** | Non-Smoker | 5,269.2 | 38 | 29.3 | **129.55%** | 91.68% | 177.82% | $9,600,000 | $8,348,193 | **114.99%** | 0.138 | **104.08%** |
| **55 – 64** | Smoker | 1,180.1 | 12 | 13.5 | **88.94%** | 45.96% | 155.36% | $3,570,000 | $3,880,349 | **92.00%** | 0.080 | **99.11%** |
| **65+** | Non-Smoker | 1,861.4 | 17 | 27.1 | **62.77%** | 36.57% | 100.50% | $7,450,000 | $7,391,173 | **100.80%** | 0.099 | **96.33%** |
| **65+** | Smoker | 416.5 | 9 | 12.1 | **74.15%** | 33.91% | 140.76% | $2,800,000 | $3,162,126 | **88.55%** | 0.075 | **98.07%** |
| **Total** | **All Cohorts** | **34,446.5** | **140** | **134.9** | **103.79%** | **87.31%** | **122.48%** | **$46,280,000** | **$38,115,897** | **121.42%** | **0.240** | **100.93%** |

### Actuarial Interpretation:
* **The Power of Credibility Weighting:** In the young cohort (`< 35 NS`), four observed deaths produced an apparent $A/E$ of $183.96\%$. A naive underwriter might panic and raise rates by $+84\%$. However, with only 4 claims, the partial credibility factor is a meager $Z = 0.044$. Our credibility engine shrinks this volatile anomaly to a reasonable **$103.73\%$**, shielding the cedant and reinsurer from reactionary overpricing.
* **Zero Claims Handling:** For `< 35 SM`, where 0 deaths were observed, traditional asymptotic formulas yield a broken $0 \pm 0\%$ interval. Our Garwood Poisson engine correctly constructs a rigorous upper $95\%$ bound of **$325.17\%$**, quantifying the true catastrophic capacity of unobserved events.

---

## 📊 Actuarial GLM Experience Rating Multipliers

To separate simultaneous age, gender, smoking, and underwriting impacts, a Poisson GLM was fitted with an exact $\ln(\text{Exposure})$ offset:

| Parameter | Coefficient ($\beta$) | Standard Error | $z$-Statistic | $p$-Value | Relativity ($\exp(\beta)$) | 95% Confidence Interval | Underwriting Interpretation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Intercept ($\beta_0$)** | -5.8136 | 0.1882 | -30.90 | $< 0.0001$ | 0.0030 | [0.0021, 0.0043] | Baseline baseline hazard for Female, Non-Smoker, Preferred |
| **Gender: Male (`T.M`)** | +0.4225 | 0.1781 | +2.37 | **0.0177** | **1.526** | **[1.076, 2.163]** | **+52.6% excess mortality** over female lives |
| **Smoker Status: Smoker (`T.SM`)** | +0.4236 | 0.1953 | +2.17 | **0.0300** | **1.528** | **[1.042, 2.240]** | **+52.8% excess mortality** over non-smokers |
| **UW: Preferred Plus** | -0.5219 | 0.2794 | -1.87 | **0.0618** | **0.593** | **[0.343, 1.026]** | **-40.7% mortality discount** for pristine underwriting |
| **UW: Standard** | -0.0201 | 0.1992 | -0.10 | 0.9196 | **0.980** | [0.663, 1.448] | Statistically indistinguishable from baseline |
| **UW: Substandard** | +0.3995 | 0.2543 | +1.57 | 0.1162 | **1.491** | [0.906, 2.455] | **+49.1% mortality loading** for impaired lives |

---

## 🔬 Empirical Bayes Credibility Variance Decomposition

Fitting the longitudinal experience of cedants via the **Bühlmann-Straub empirical Bayes model** yields the core variance components:

* **Expected Value of Process Variance (EPV / $s^2$):** $3.046854 \times 10^{-3}$
* **Variance of Hypothetical Means (VHM / $a$):** $1.831601 \times 10^{-7}$
* **Bühlmann Constant ($k^* = s^2 / a$):** **$16,634.9$ life-years**
* **Portfolio Grand Mean ($\mu$):** **$0.0041$ deaths per life-year**

### Actuarial Implication:
The high Bühlmann parameter ($k^* \approx 16,635$) indicates that within-cedant process variance significantly dominates between-cedant variation. A ceding company requires upwards of $16,000$ life-years of exposure before their own historical claims achieve $50\%$ credibility weighting ($Z = 0.50$). This prevents premature rate adjustments based on transitory claims spikes.

---

## 🛡️ Stochastic Reinsurance Treaty Risk Transfer & Solvency II Capital Relief

A stochastic simulation of **10,000 portfolio years** was executed across a calibrated compound Poisson-Pareto collective risk process ($\lambda = 25.0, \alpha = 1.85, x_m = \$500,000$) protected by a two-tier reinsurance program:
- **Working Layer:** $\$1.5\text{M xs } \$500\text{k}$
- **Catastrophe Layer:** $\$8.0\text{M xs } \$2.0\text{M}$

```
SOLVENCY II 1-IN-200 YEAR UNDERWRITING RISK PROFILE
══════════════════════════════════════════════════════════════════
Gross Expected Annual Loss:           $38,706,113.63
Net Retained Expected Annual Loss:    $17,086,792.64
──────────────────────────────────────────────────────────────────
Gross 99.5% VaR (1-in-200 PML):       $87,948,627.52
Net Retained 99.5% VaR:               $48,078,627.34
Reduction in 99.5% VaR:              -$39,870,000.18 (-45.3%)
──────────────────────────────────────────────────────────────────
Gross 99.5% TVaR (Expected Shortfall):$130,285,371.69
Net Retained 99.5% TVaR:              $89,044,200.29
Reduction in Tail Severity:          -$41,241,171.40 (-31.7%)
══════════════════════════════════════════════════════════════════
Gross Underwriting SCR Requirement:   $49,242,513.89
Net Underwriting SCR Requirement:     $30,991,834.70
──────────────────────────────────────────────────────────────────
TOTAL SOLVENCY CAPITAL RELIEF:        $18,250,679.19
PERCENTAGE SCR REDUCTION:                      37.1%
══════════════════════════════════════════════════════════════════
```

### Visual Evidence:
The following high-resolution 300-DPI charts illustrate these dynamics:

1. **Mortality A/E Experience & Garwood CIs:**
   ![Mortality A/E Experience](assets/mortality_ae_experience.png)
   *Displays actual-to-expected mortality across age cohorts with exact Poisson error bars and life-years exposure bars.*

2. **Reinsurance Aggregate Exceedance Probability (AEP) Curve:**
   ![Reinsurance AEP Curve](assets/reinsurance_aep_curve.png)
   *Contrasts gross vs net retained loss distributions, showing massive 45.3% reduction at the 1-in-200 year Solvency II threshold.*

3. **Credibility Convergence Curve ($Z$ vs $n$):**
   ![Credibility Convergence](assets/credibility_convergence.png)
   *Demonstrates the non-linear convergence of credibility weight $Z$ toward 1.0 as claim count approaches the 1,082-claim standard.*

---

## ⚡ Computational Performance & Benchmarking

All calculations were executed locally on a standard workstation:

| Benchmark Task | Data Volume / Iterations | Execution Time | Memory Footprint |
| :--- | :--- | :--- | :--- |
| **Longitudinal Policy Exposure Engine** | 15,000 policies (34k life-years) | **0.18 seconds** | ~35 MB |
| **SOA VBT Benchmark Attachment** | 15,000 records matched by age/gender | **0.04 seconds** | ~12 MB |
| **A/E Study & Garwood Poisson Intervals** | 10 demographic cohorts | **0.02 seconds** | < 5 MB |
| **Actuarial GLM with Exposure Offset** | 15,000 rows x 5 covariates | **0.12 seconds** | ~45 MB |
| **Bühlmann-Straub Credibility Fitting** | Longitudinal multi-cedant panel | **0.01 seconds** | < 2 MB |
| **10,000-Trial Monte Carlo Reinsurance Simulation** | 10,000 portfolio years across 2 layers | **0.45 seconds** | ~60 MB |
| **Solvency II VaR / TVaR / SCR Relief Engine** | 10,000 loss vectors evaluated | **0.03 seconds** | < 5 MB |
| **300-DPI Publication Figures & Dual Reports** | 3 PNGs, Markdown & Standalone HTML | **0.85 seconds** | ~85 MB |
| **TOTAL END-TO-END RUNTIME** | **Full Pipeline Execution** | **< 3.2 seconds** | **~85 MB Peak** |

### Benchmark Takeaway:
What requires **4 to 8 hours** of manual data wrangling, formula debugging, and macro execution in Microsoft Excel—or **30 to 90 minutes** of batch queuing in legacy software—runs on our engine in **3.2 seconds** with zero human intervention and 100% mathematical auditability.

---

## 🧭 Related Documentation
- 🔄 [**End-to-End Quantitative Process**](process.md)
- ⚡ [**Technologies Used & Market Practice Comparison**](technologies_used.md)
- 📐 [**Actuarial Methodology & Mathematical Foundations**](actuarial_methodology.md)
- 🏗️ [**Reinsurance Treaty Structures**](treaty_structures.md)
- 🏠 [**Project Main Page (README)**](../README.md)
