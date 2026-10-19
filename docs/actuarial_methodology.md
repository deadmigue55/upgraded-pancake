# Actuarial Methodology & Mathematical Foundations

This document details the quantitative methods, statistical models, and probability distributions implemented in `reinsurance-analytics`.

---

## 1. Exposure Measurement

Accurate calculation of policy exposure is the prerequisite for any actuarial experience study.

### 1.1 Exact Continuous (Daily) Exposure
For a policy issued at date $T_{\text{issue}}$ exiting at date $T_{\text{exit}}$ evaluated over study interval $[T_{\text{start}}, T_{\text{end}}]$:

$$e_i = \frac{\max\left(0, \min(T_{\text{end}}, T_{\text{exit}}) - \max(T_{\text{start}}, T_{\text{issue}})\right)}{365.25}$$

### 1.2 Balducci Assumption (Annual Exposure)
Under the classical Balducci hypothesis, if an individual dies during the observation period, they are exposed to the risk of death for the remainder of the policy year:

$$e_i^{\text{Balducci}} = \begin{cases} 
e_i + (1 - f_i), & \text{if claim event occurred in policy year} \\
e_i, & \text{otherwise}
\end{cases}$$

where $f_i$ is the fraction of policy year elapsed prior to death.

---

## 2. Actual-to-Expected ($A/E$) Mortality Analysis

### 2.1 Actual vs. Expected Ratios
Given actual claims $A$ and expected claims $E = \sum_i e_i \cdot q_{x_i}$:

$$\text{A/E}_{\text{count}} = \frac{\sum_{i=1}^n \mathbb{I}(\text{Event}_i)}{\sum_{i=1}^n e_i \cdot q_{x_i}^{\text{benchmark}}}$$

$$\text{A/E}_{\text{amount}} = \frac{\sum_{i=1}^n \text{Claim Amount}_i}{\sum_{i=1}^n e_i \cdot \text{Amount}_i \cdot q_{x_i}^{\text{benchmark}}}$$

### 2.2 Garwood Exact Poisson Confidence Intervals
Because claim counts follow a Poisson distribution $A \sim \text{Poisson}(\lambda)$, the gold standard for confidence intervals adopted by the Society of Actuaries (SOA) uses the exact Chi-Square equivalence:

$$\text{CI}_{1-\alpha} = \left[ \frac{\chi^2_{2A, \, \alpha/2}}{2E}, \; \frac{\chi^2_{2(A+1), \, 1 - \alpha/2}}{2E} \right]$$

For $A = 0$:
$$\text{CI}_{1-\alpha} = \left[ 0, \; \frac{\chi^2_{2, \, 1 - \alpha}}{2E} \right]$$

---

## 3. Credibility Theory

Reinsurance portfolios typically have limited historical experience for rare catastrophic or high-layer events.

### 3.1 Classical / Limited Fluctuation Credibility
We require actual claims to be within margin $k$ of expected claims with probability $p = 1 - \alpha$:

$$\mathbb{P}\left(|\bar{X} - \mu| \le k\mu\right) = 1 - \alpha$$

The full credibility standard for Poisson claim counts is:

$$n^* = \left(\frac{z_{1 - \alpha/2}}{k}\right)^2 \left(1 + \frac{\text{Var}(X)}{\mathbb{E}[X]^2}\right) = \left(\frac{z_{1 - \alpha/2}}{k}\right)^2 (1 + CV_X^2)$$

For $p = 90\%$ ($z_{0.95} = 1.64485$) and $k = 5\%$ ($0.05$):
$$n^* = \left(\frac{1.64485}{0.05}\right)^2 \approx 1,082.41 \text{ claims}$$

For sample count $n < n^*$, partial credibility factor $Z$ is:
$$Z = \min\left(1.0, \sqrt{\frac{n}{n^*}}\right)$$

The credibility-weighted experience estimate is:
$$\hat{\mu} = Z \cdot \bar{X} + (1 - Z) \cdot M$$

### 3.2 Bühlmann-Straub Empirical Bayes Credibility
For heterogeneous treaties/cedants $i = 1, \dots, k$ observed over periods $t = 1, \dots, T_i$ with exposure $P_{it}$ and loss ratio $X_{it}$:

1. **Expected Value of Process Variance (EPV / $s^2$):**
   $$s^2 = \frac{1}{\sum_{i=1}^k (T_i - 1)} \sum_{i=1}^k \sum_{t=1}^{T_i} P_{it} (X_{it} - \bar{X}_i)^2$$

2. **Variance of Hypothetical Means (VHM / $a$):**
   $$a = \max\left(0, \frac{\sum_{i=1}^k P_{i\cdot}(\bar{X}_i - \bar{X})^2 - (k - 1) s^2}{P_{\cdot\cdot} - \sum_{i=1}^k P_{i\cdot}^2 / P_{\cdot\cdot}}\right)$$

3. **Bühlmann Credibility Factor:**
   $$Z_i = \frac{P_{i\cdot}}{P_{i\cdot} + k^*}, \quad k^* = \frac{s^2}{a}$$

---

## 4. Generalized Linear Models (GLMs) with Offset

Experience rating relativities are estimated via Poisson GLM with canonical log link:

$$\ln(\mathbb{E}[Y_i]) = \ln(\text{Exposure}_i) + \beta_0 + \sum_{j=1}^p \beta_j X_{ij}$$

The multiplicative risk relativity for covariate level $j$ is:
$$\text{Relativity}_j = \exp(\beta_j)$$

---

## 5. Extreme Value Theory (EVT) & Tail Severity

### 5.1 Peaks-Over-Threshold (POT)
For high threshold $u$, excess losses $Y = X - u \mid X > u$ follow Generalized Pareto Distribution (GPD):

$$F_u(y) = 1 - \left(1 + \frac{\xi y}{\sigma}\right)^{-1/\xi}$$

### 5.2 Hill Estimator
For ordered upper statistics $X_{(1)} \ge X_{(2)} \ge \dots \ge X_{(n)}$:

$$\hat{\xi} = \frac{1}{k} \sum_{j=1}^k \ln\left(\frac{X_{(j)}}{X_{(k+1)}}\right), \quad \hat{\alpha} = \frac{1}{\hat{\xi}}$$

---

## 6. Collective Risk Modeling & Panjer Recursion

Aggregate portfolio loss is modeled as:
$$S = \sum_{i=1}^N X_i$$

### Panjer Recursion Algorithm
For frequency $N$ in the $(a, b, 0)$ distribution family ($p_k = (a + b/k) p_{k-1}$):

$$g_0 = P_N(f_0)$$
$$g_k = \frac{1}{1 - a f_0} \sum_{j=1}^k \left(a + \frac{b j}{k}\right) f_j g_{k-j}$$

For Poisson($\lambda$): $a = 0, b = \lambda \implies g_k = \frac{\lambda}{k} \sum_{j=1}^k j f_j g_{k-j}$.

---

## 7. Solvency II Capital Relief

$$\text{SCR} = \text{VaR}_{0.995}(S) - \mathbb{E}[S]$$
$$\text{Capital Relief} = \text{SCR}_{\text{Gross}} - \text{SCR}_{\text{Net}}$$
