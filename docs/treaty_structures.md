# Reinsurance Treaty Structures & Mathematical Layering

This guide outlines the standard reinsurance treaty contracts supported by `reinsurance-analytics`.

---

## 1. Proportional Reinsurance

### 1.1 Quota Share
The cedant cedes a fixed percentage $c \in [0, 1]$ of every policy's sum insured, premium, and losses.
- **Ceded Premium:** $P_{\text{ceded}} = c \cdot P_{\text{gross}}$
- **Ceding Commission:** $C_{\text{comm}} = c \cdot P_{\text{gross}} \cdot \text{commission\_rate}$
- **Ceded Loss:** $L_{\text{ceded}} = c \cdot L_{\text{gross}}$
- **Cedant Retention:** $L_{\text{retained}} = (1 - c) \cdot L_{\text{gross}}$

### 1.2 Surplus Treaty
The cedant retains up to a specified monetary capacity (Line Retention $R$). Policies with sum insured $\text{SI} > R$ are ceded in lines up to maximum $n$ lines:
- **Cession Ratio:**
  $$\alpha_i = \min\left(\frac{n \cdot R}{\text{SI}_i}, \, \max\left(0, \frac{\text{SI}_i - R}{\text{SI}_i}\right)\right)$$
- **Ceded Loss:** $L_{\text{ceded}, i} = \alpha_i \cdot L_{\text{gross}, i}$

---

## 2. Non-Proportional Reinsurance

### 2.1 Excess of Loss (XL) - Limit xs Attachment
Denoted $L \text{ xs } A$ (e.g., $10\text{M xs } \$5\text{M}$):
- **Recovery per Loss Event:**
  $$\text{Recovery}(X) = \min(\max(0, X - A), L)$$
- **Cedant Net Retained Loss:**
  $$\text{Net}(X) = X - \text{Recovery}(X)$$

### 2.2 Reinstatement Clauses
When a loss erodes the layer limit $L$, reinstatements restore cover up to $n$ times:
- **Pro-Rata as to Amount:**
  $$\text{Reinstatement Premium} = \frac{\text{Claim Ceded}}{L} \times \text{Rate} \times \text{Initial Premium}$$
- **Pro-Rata as to Time and Amount:**
  $$\text{Reinstatement Premium} = \frac{\text{Claim Ceded}}{L} \times \frac{\text{Days Remaining}}{365.25} \times \text{Rate} \times \text{Initial Premium}$$

---

## 3. Aggregate Stop Loss
Protects against high overall annual loss ratio or cumulative portfolio claim volume:
$$\text{Stop Loss Recovery}(S) = \min(\max(0, S - A_{\text{agg}}), L_{\text{agg}})$$
where $S = \sum_{i=1}^N X_i$ is annual aggregate loss.
